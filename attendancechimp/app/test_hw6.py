"""Tests for HW6 course-schedule validation and the getUploads endpoint."""

from datetime import datetime, time, timedelta, timezone as datetime_timezone
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import Client, TestCase

from .models import (
    Course,
    InstructorProfile,
    Lecture,
    QRCodeUpload,
    StudentProfile,
    getUploadsForCourse,
)


CHICAGO = ZoneInfo("America/Chicago")


class HomeworkSixTests(TestCase):
    def setUp(self):
        self.instructor_user = User.objects.create_user(
            username="professor",
            password="safe-password",
        )
        self.instructor = InstructorProfile.objects.create(
            user=self.instructor_user,
            employee_id="EMP-600",
        )
        self.student_user = User.objects.create_user(
            username="alice",
            password="safe-password",
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            student_id="STU-600",
        )
        self.course = Course.objects.create(
            course="DATA13600",
            course_code="DATA13600",
            name="Data Engineering Platforms",
            instructor=self.instructor,
            meeting_schedule="Mon/Wed/Fri 10:00-11:20",
            start_time=time(10, 0),
            end_time=time(11, 20),
            mon=True,
            wed=True,
            fri=True,
        )
        self.other_course = Course.objects.create(
            course="OTHER200",
            course_code="OTHER200",
            name="Another Course",
            instructor=self.instructor,
            meeting_schedule="Mon 10:00-11:20",
            start_time="10:00",
            end_time="11:20",
            monday=True,
        )

        self.instructor_client = Client()
        self.instructor_client.force_login(self.instructor_user)
        self.student_client = Client()
        self.student_client.force_login(self.student_user)

    def _chicago_datetime(self, year, month, day, hour, minute):
        return datetime(year, month, day, hour, minute, tzinfo=CHICAGO)

    def _upload_at(self, course, local_timestamp):
        lecture = Lecture.objects.create(
            course=course,
            date=local_timestamp + timedelta(seconds=Lecture.objects.count()),
            is_open=True,
        )
        upload = QRCodeUpload.objects.create(student=self.student, lecture=lecture)
        utc_timestamp = local_timestamp.astimezone(datetime_timezone.utc)
        QRCodeUpload.objects.filter(pk=upload.pk).update(upload_time=utc_timestamp)
        upload.refresh_from_db()
        return upload

    def test_helper_includes_a_valid_upload(self):
        valid = self._upload_at(
            self.course,
            self._chicago_datetime(2024, 11, 4, 10, 30),
        )
        self.assertEqual(getUploadsForCourse("DATA13600"), [valid])

    def test_helper_returns_empty_list_for_unknown_course(self):
        self.assertEqual(getUploadsForCourse("DOES-NOT-EXIST"), [])

    def test_helper_excludes_uploads_for_other_courses(self):
        valid = self._upload_at(
            self.course,
            self._chicago_datetime(2024, 11, 4, 10, 30),
        )
        self._upload_at(
            self.other_course,
            self._chicago_datetime(2024, 11, 4, 10, 30),
        )
        self.assertEqual(getUploadsForCourse("DATA13600"), [valid])

    def test_helper_filters_nonmeeting_days_and_weekends(self):
        monday = self._upload_at(
            self.course,
            self._chicago_datetime(2024, 11, 4, 10, 30),
        )
        self._upload_at(
            self.course,
            self._chicago_datetime(2024, 11, 5, 10, 30),
        )
        self._upload_at(
            self.course,
            self._chicago_datetime(2024, 11, 9, 10, 30),
        )
        self.assertEqual(getUploadsForCourse("DATA13600"), [monday])

    def test_helper_filters_times_outside_class_and_keeps_boundaries(self):
        before = self._upload_at(
            self.course,
            self._chicago_datetime(2024, 11, 4, 9, 59),
        )
        at_start = self._upload_at(
            self.course,
            self._chicago_datetime(2024, 11, 4, 10, 0),
        )
        at_end = self._upload_at(
            self.course,
            self._chicago_datetime(2024, 11, 4, 11, 20),
        )
        after = self._upload_at(
            self.course,
            self._chicago_datetime(2024, 11, 4, 11, 21),
        )
        self.assertEqual(set(getUploadsForCourse("DATA13600")), {at_start, at_end})
        self.assertNotIn(before, getUploadsForCourse("DATA13600"))
        self.assertNotIn(after, getUploadsForCourse("DATA13600"))

    def test_helper_checks_chicago_time_instead_of_utc_clock_time(self):
        chicago_valid = self._upload_at(
            self.course,
            datetime(2024, 11, 4, 16, 30, tzinfo=datetime_timezone.utc),
        )
        utc_1030_is_too_early_in_chicago = self._upload_at(
            self.course,
            datetime(2024, 11, 4, 10, 30, tzinfo=datetime_timezone.utc),
        )
        results = getUploadsForCourse("DATA13600")
        self.assertIn(chicago_valid, results)
        self.assertNotIn(utc_1030_is_too_early_in_chicago, results)

    def test_get_uploads_is_instructor_only(self):
        url = "/app/getUploads?course=DATA13600"
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.student_client.get(url).status_code, 401)
        self.assertEqual(self.instructor_client.get(url).status_code, 200)

    def test_get_uploads_requires_course_parameter(self):
        response = self.instructor_client.get("/app/getUploads")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Missing course parameter"})

    def test_get_uploads_returns_empty_list_for_unknown_course(self):
        response = self.instructor_client.get("/app/getUploads?course=UNKNOWN")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_uploads_returns_exact_json_for_valid_uploads(self):
        valid = self._upload_at(
            self.course,
            self._chicago_datetime(2024, 11, 4, 10, 30),
        )
        self._upload_at(
            self.course,
            self._chicago_datetime(2024, 11, 5, 10, 30),
        )
        response = self.instructor_client.get("/app/getUploads?course=DATA13600")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [{"username": "alice", "upload_time": "2024-11-04 10:30:00"}],
        )
        self.assertEqual(getUploadsForCourse("DATA13600"), [valid])
