"""Focused tests for the Homework 3 data model and its constraints."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from .models import (
    Course,
    Enrollment,
    InstructorProfile,
    Lecture,
    QRCodeUpload,
    StudentProfile,
)


class AttendanceChimpModelTests(TestCase):
    def setUp(self):
        instructor_user = User.objects.create_user(username="professor")
        student_user = User.objects.create_user(username="student")
        self.instructor = InstructorProfile.objects.create(
            user=instructor_user,
            employee_id="EMP-100",
        )
        self.student = StudentProfile.objects.create(
            user=student_user,
            student_id="STU-100",
        )
        self.course = Course.objects.create(
            course_code="DATA13600",
            name="Data Engineering Platforms",
            instructor=self.instructor,
            meeting_schedule="Tue/Thu 9:30-10:50 AM",
        )
        self.lecture = Lecture.objects.create(
            course=self.course,
            date=timezone.now() + timedelta(days=1),
            is_open=True,
        )

    def test_course_enrollment_exposes_student(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        self.assertQuerySetEqual(self.course.students.all(), [self.student])

    def test_duplicate_enrollment_is_rejected(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Enrollment.objects.create(student=self.student, course=self.course)

    def test_qr_match_helper(self):
        upload = QRCodeUpload.objects.create(
            student=self.student,
            lecture=self.lecture,
            submitted_qr_identifier=self.lecture.qr_identifier,
        )
        self.assertTrue(upload.matches_lecture())

    def test_second_upload_for_same_lecture_is_rejected(self):
        QRCodeUpload.objects.create(student=self.student, lecture=self.lecture)
        with self.assertRaises(IntegrityError), transaction.atomic():
            QRCodeUpload.objects.create(student=self.student, lecture=self.lecture)


