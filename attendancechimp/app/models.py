"""Core relational data model for AttendanceChimp.

Authentication stays in Django's built-in ``User`` table. Separate one-to-one
profiles hold role-specific identifiers, so one person can be a student, an
instructor, or both without duplicating login data. Courses belong to an
instructor, students join courses through ``Enrollment``, lectures belong to a
course, and every QR-code upload identifies its student and optional lecture.

Database constraints encode the rules that are cheapest and safest to enforce
centrally: a student can enroll in a course only once, a lecture has a unique
unpredictable QR value, and a student cannot submit twice for the same lecture.
"""

import uuid

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q


class InstructorProfile(models.Model):
    """Role-specific data for a user who teaches one or more courses.

    ``PROTECT`` is used from ``Course`` to this model so deleting an instructor
    cannot silently erase the historical ownership of a course.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="instructor_profile",
    )
    employee_id = models.CharField(max_length=32, unique=True)
    department = models.CharField(max_length=100, blank=True)
    office_location = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["employee_id"]

    def __str__(self):
        """Return a helpful label for admin pages and logs."""
        return f"{self.user.get_full_name() or self.user.username} ({self.employee_id})"


class StudentProfile(models.Model):
    """Role-specific data for a user who may enroll in courses."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    student_id = models.CharField(max_length=32, unique=True)
    graduation_year = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["student_id"]

    def __str__(self):
        """Return a helpful label for admin pages and reports."""
        return f"{self.user.get_full_name() or self.user.username} ({self.student_id})"


class Course(models.Model):
    """A course section taught by exactly one instructor.

    ``meeting_schedule`` deliberately remains human-readable because this
    assignment models storage rather than calendar recurrence behavior.
    """

    course_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    instructor = models.ForeignKey(
        InstructorProfile,
        on_delete=models.PROTECT,
        related_name="courses",
    )
    meeting_schedule = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    students = models.ManyToManyField(
        StudentProfile,
        through="Enrollment",
        related_name="courses",
    )

    class Meta:
        ordering = ["course_code"]

    def __str__(self):
        """Return the catalog-style course label."""
        return f"{self.course_code}: {self.name}"


class Enrollment(models.Model):
    """Explicit join table connecting students to courses.

    Keeping enrollment as its own entity allows later homework to query active
    rosters and preserve the timestamp at which a student joined a course.
    """

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["course__course_code", "student__student_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_enrollment",
            )
        ]

    def __str__(self):
        """Describe the student-course relationship."""
        return f"{self.student} enrolled in {self.course.course_code}"


class Lecture(models.Model):
    """One scheduled meeting of a course with a unique QR identifier.

    UUID values are difficult to guess and can be rotated by creating a new
    lecture, which is safer than using a short sequential QR value.
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lectures",
    )
    date = models.DateTimeField()
    qr_identifier = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_open = models.BooleanField(default=False)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "date"],
                name="unique_course_lecture_datetime",
            )
        ]

    def __str__(self):
        """Return a readable course-and-date label."""
        return f"{self.course.course_code} lecture at {self.date:%Y-%m-%d %H:%M}"


class QRCodeUpload(models.Model):
    """A student's uploaded QR-code photo and its validation metadata.

    The lecture is optional so an upload can be retained for investigation even
    when no lecture is recognized. ``image_digest`` may contain a SHA-256 hash;
    making it unique detects reuse of an identical image across submissions.
    """

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="qr_code_uploads",
    )
    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="qr_code_uploads",
    )
    image = models.FileField(upload_to="qr_uploads/%Y/%m/%d/", blank=True)
    submitted_qr_identifier = models.UUIDField(null=True, blank=True)
    image_digest = models.CharField(max_length=64, unique=True, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField(default=False)

    class Meta:
        ordering = ["-uploaded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "lecture"],
                condition=Q(lecture__isnull=False),
                name="one_upload_per_student_lecture",
            )
        ]

    def matches_lecture(self):
        """Return whether the decoded QR value matches the linked lecture."""
        return bool(
            self.lecture_id
            and self.submitted_qr_identifier
            and self.submitted_qr_identifier == self.lecture.qr_identifier
        )

    def __str__(self):
        """Identify the student and target lecture, when known."""
        target = str(self.lecture) if self.lecture_id else "unmatched lecture"
        return f"Upload from {self.student} for {target}"
