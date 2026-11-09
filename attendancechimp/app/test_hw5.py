"""End-to-end tests for the Homework 5 forms and role-protected endpoints."""

import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from .models import Course, InstructorProfile, Lecture, QRCodeUpload, StudentProfile


class HomeworkFiveTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._media_directory = tempfile.TemporaryDirectory()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_directory.name)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        cls._media_directory.cleanup()

    def setUp(self):
        self.instructor_user = User.objects.create_user(
            username="professor", password="safe-password"
        )
        self.instructor = InstructorProfile.objects.create(
            user=self.instructor_user,
            employee_id="EMP-500",
        )
        self.student_user = User.objects.create_user(
            username="student", password="safe-password"
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            student_id="STU-500",
        )
        self.course = Course.objects.create(
            course_code="DATA13600",
            name="Data Engineering Platforms",
            instructor=self.instructor,
            meeting_schedule="Tue/Thu 09:30-10:50",
        )

        self.instructor_client = Client()
        self.instructor_client.force_login(self.instructor_user)
        self.student_client = Client()
        self.student_client.force_login(self.student_user)

    def _image(self, name="qr-code.png"):
        return SimpleUploadedFile(name, b"not-a-real-png", content_type="image/png")

    def test_required_forms_are_available_and_submit_to_the_right_endpoints(self):
        course_page = self.client.get("/app/new_course")
        self.assertEqual(course_page.status_code, 200)
        self.assertContains(course_page, 'action="/app/createCourse/"')
        for field_name in (
            "course-name",
            "start-time",
            "end-time",
            "day-mon",
            "day-tue",
            "day-wed",
            "day-thu",
            "day-fri",
        ):
            self.assertContains(course_page, f'name="{field_name}"')

        lecture_page = self.client.get("/app/new_lecture")
        self.assertEqual(lecture_page.status_code, 200)
        self.assertContains(lecture_page, 'action="/app/createLecture/"')
        self.assertContains(lecture_page, 'name="choice"')
        self.assertContains(lecture_page, self.course.name)

        upload_page = self.client.get("/app/new_qr_upload")
        self.assertEqual(upload_page.status_code, 200)
        self.assertContains(upload_page, 'action="/app/createQRCodeUpload/"')
        self.assertContains(upload_page, 'enctype="multipart/form-data"')
        self.assertContains(upload_page, 'name="imageUpload"')

    def test_only_instructors_can_create_courses(self):
        data = {
            "course-name": "CS103",
            "start-time": "12:00",
            "end-time": "13:20",
            "day-mon": "1",
        }
        before = Course.objects.count()
        self.assertEqual(self.client.post("/app/createCourse/", data).status_code, 401)
        self.assertEqual(
            self.student_client.post("/app/createCourse/", data).status_code, 401
        )
        self.assertEqual(Course.objects.count(), before)

        response = self.instructor_client.post("/app/createCourse/", data)
        self.assertEqual(response.status_code, 200)
        created = Course.objects.get(name="CS103")
        self.assertEqual(created.instructor, self.instructor)
        self.assertEqual(created.meeting_schedule, "Mon 12:00-13:20")

    def test_invalid_course_input_does_not_create_a_row(self):
        before = Course.objects.count()
        response = self.instructor_client.post(
            "/app/createCourse/",
            {"course-name": "No Days", "start-time": "12:00", "end-time": "13:20"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Course.objects.count(), before)

    def test_only_instructors_can_create_lectures(self):
        data = {"choice": self.course.name}
        self.assertEqual(self.client.post("/app/createLecture/", data).status_code, 401)
        self.assertEqual(
            self.student_client.post("/app/createLecture/", data).status_code, 401
        )
        self.assertEqual(Lecture.objects.count(), 0)

        response = self.instructor_client.post("/app/createLecture/", data)
        self.assertEqual(response.status_code, 200)
        lecture = Lecture.objects.get()
        self.assertEqual(lecture.course, self.course)
        self.assertTrue(lecture.is_open)

    def test_missing_lecture_choice_does_not_create_a_row(self):
        response = self.instructor_client.post("/app/createLecture/", {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Lecture.objects.count(), 0)

    def test_only_students_can_upload_qr_images(self):
        self.assertEqual(
            self.client.post(
                "/app/createQRCodeUpload/", {"imageUpload": self._image("anon.png")}
            ).status_code,
            401,
        )
        self.assertEqual(
            self.instructor_client.post(
                "/app/createQRCodeUpload/",
                {"imageUpload": self._image("instructor.png")},
            ).status_code,
            401,
        )
        self.assertEqual(QRCodeUpload.objects.count(), 0)

        response = self.student_client.post(
            "/app/createQRCodeUpload/", {"imageUpload": self._image()}
        )
        self.assertEqual(response.status_code, 200)
        upload = QRCodeUpload.objects.get()
        self.assertEqual(upload.student, self.student)
        self.assertTrue(upload.image.name.startswith("qr_uploads/"))
        self.assertTrue(upload.image.name.endswith(".png"))

    def test_missing_image_does_not_create_an_upload(self):
        response = self.student_client.post("/app/createQRCodeUpload/", {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(QRCodeUpload.objects.count(), 0)

    def test_dump_uploads_is_instructor_only_and_has_exact_keys(self):
        QRCodeUpload.objects.create(student=self.student, image=self._image())
        self.assertEqual(self.client.get("/app/dumpUploads").status_code, 401)
        self.assertEqual(self.student_client.get("/app/dumpUploads").status_code, 401)

        response = self.instructor_client.get("/app/dumpUploads")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(set(payload[0]), {"username", "upload_time"})
        self.assertEqual(payload[0]["username"], "student")
        self.assertTrue(payload[0]["upload_time"])

    def test_hw5_endpoints_reject_wrong_http_methods(self):
        self.assertEqual(self.instructor_client.get("/app/createCourse/").status_code, 405)
        self.assertEqual(self.instructor_client.get("/app/createLecture/").status_code, 405)
        self.assertEqual(self.student_client.get("/app/createQRCodeUpload/").status_code, 405)
        self.assertEqual(self.instructor_client.post("/app/dumpUploads").status_code, 405)
