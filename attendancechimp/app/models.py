"""Core relational data model for AttendanceChimp.

Authentication stays in Django's built-in ``User`` table. Separate one-to-one
profiles hold role-specific identifiers, so one person can be a student, an
instructor, or both without duplicating login data. Courses belong to an
instructor, students join courses through ``Enrollment``, lectures belong to a
course, and every QR-code upload identifies its student and optional lecture.

Database constraints encode the rules that are cheapest and safest to enforce
centrally: a student can enroll in a course only once, a lecture has a unique
unpredictable QR value, and every upload remains available for validation.
"""

import uuid
from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


CHICAGO_TIME_ZONE = ZoneInfo("America/Chicago")


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


def _field_alias(field_name):
    """Create a read/write property that aliases a model field."""

    def getter(instance):
        return getattr(instance, field_name)

    def setter(instance, value):
        setattr(instance, field_name, value)

    return property(getter, setter)


class Course(models.Model):
    """A course section taught by exactly one instructor.

    ``meeting_schedule`` deliberately remains human-readable because this
    assignment models storage rather than calendar recurrence behavior.
    """

    # ``course`` is the unique course-number field used by HW6 (for example,
    # DATA13600). ``course_code`` is retained for compatibility with HW3-HW5.
    course = models.CharField(max_length=20, unique=True, null=True, blank=True)
    course_code = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200, blank=True)
    instructor = models.ForeignKey(
        InstructorProfile,
        on_delete=models.PROTECT,
        related_name="courses",
    )
    meeting_schedule = models.CharField(max_length=200, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    mon = models.BooleanField(default=False)
    tue = models.BooleanField(default=False)
    wed = models.BooleanField(default=False)
    thu = models.BooleanField(default=False)
    fri = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    students = models.ManyToManyField(
        StudentProfile,
        through="Enrollment",
        related_name="courses",
    )

    class Meta:
        ordering = ["course_code"]

    def meets_on_day(self, weekday):
        """Return whether the course meets on a given weekday.

        ``weekday`` may be the integer returned by ``datetime.weekday()`` or a
        weekday name/abbreviation. Weekends always return ``False``.
        """
        if isinstance(weekday, str):
            normalized = weekday.strip().lower()[:3]
            weekday = {
                "mon": 0,
                "tue": 1,
                "wed": 2,
                "thu": 3,
                "fri": 4,
                "sat": 5,
                "sun": 6,
            }.get(normalized)
        fields = ("mon", "tue", "wed", "thu", "fri")
        if not isinstance(weekday, int) or weekday not in range(len(fields)):
            return False
        return bool(getattr(self, fields[weekday]))

    # Read/write aliases make the schedule easy to use with either full weekday
    # names or the short names used by the HW5 form fields.
    monday = _field_alias("mon")
    tuesday = _field_alias("tue")
    wednesday = _field_alias("wed")
    thursday = _field_alias("thu")
    friday = _field_alias("fri")
    day_mon = _field_alias("mon")
    day_tue = _field_alias("tue")
    day_wed = _field_alias("wed")
    day_thu = _field_alias("thu")
    day_fri = _field_alias("fri")

    def __str__(self):
        """Return the catalog-style course label."""
        number = self.course or self.course_code or "Unnumbered course"
        return f"{number}: {self.name}" if self.name else number


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
    # Some course implementations call the timestamp ``upload_time``. New
    # browser uploads fall back to the existing ``uploaded_at`` field.
    upload_time = models.DateTimeField(null=True, blank=True)
    is_valid = models.BooleanField(default=False)

    class Meta:
        ordering = ["-uploaded_at"]

    def matches_lecture(self):
        """Return whether the decoded QR value matches the linked lecture."""
        return bool(
            self.lecture_id
            and self.submitted_qr_identifier
            and self.submitted_qr_identifier == self.lecture.qr_identifier
        )

    def effective_upload_time(self):
        """Return an explicitly assigned upload time or the creation time."""
        return self.upload_time or self.uploaded_at

    def __str__(self):
        """Identify the student and target lecture, when known."""
        target = str(self.lecture) if self.lecture_id else "unmatched lecture"
        return f"Upload from {self.student} for {target}"


def _time_value(value):
    """Normalize a model time value or HH:MM string to ``datetime.time``."""
    if isinstance(value, time):
        return value.replace(tzinfo=None)
    if isinstance(value, str):
        for time_format in ("%H:%M", "%H:%M:%S"):
            try:
                return datetime.strptime(value, time_format).time()
            except ValueError:
                continue
    return None


def getUploadsForCourse(course):
    """Return uploads made during the named course's Chicago meeting time.

    Upload timestamps are stored in UTC by Django. Each timestamp is converted
    to America/Chicago before checking its weekday and time-of-day.
    """
    course_number = str(course).strip() if course is not None else ""
    if not course_number:
        return []

    course_obj = (
        Course.objects.filter(course=course_number).first()
        or Course.objects.filter(course_code=course_number).first()
        or Course.objects.filter(name=course_number).first()
    )
    if course_obj is None:
        return []

    start_time = _time_value(course_obj.start_time)
    end_time = _time_value(course_obj.end_time)
    if start_time is None or end_time is None:
        return []

    valid_uploads = []
    uploads = QRCodeUpload.objects.filter(lecture__course=course_obj).select_related(
        "student__user",
        "lecture__course",
    )
    for upload in uploads:
        local_timestamp = timezone.localtime(
            upload.effective_upload_time(),
            CHICAGO_TIME_ZONE,
        )
        if not course_obj.meets_on_day(local_timestamp.weekday()):
            continue
        if start_time <= local_timestamp.time().replace(tzinfo=None) <= end_time:
            valid_uploads.append(upload)
    return valid_uploads
