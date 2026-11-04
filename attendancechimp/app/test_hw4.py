"""Behavior tests for the Homework 4 front-end/back-end data flow."""

import re

from django.contrib.auth.models import User
from django.test import TestCase

from .models import InstructorProfile, StudentProfile


class FrontendBackendFlowTests(TestCase):
    def test_home_page_has_required_dynamic_content(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AttendanceChimp")
        self.assertContains(response, "Not logged in.")
        self.assertRegex(response.content.decode(), re.compile(r"\d{2}:\d{2}"))

    def test_new_page_is_get_only_and_has_required_form_fields(self):
        response = self.client.get("/app/new")
        self.assertEqual(response.status_code, 200)
        for field_name in ("user_name", "email", "password", "is_student"):
            self.assertContains(response, field_name)
        self.assertContains(response, 'action="/app/createUser"')
        self.assertEqual(self.client.post("/app/new").status_code, 405)

    def test_create_user_is_post_only(self):
        self.assertEqual(self.client.get("/app/createUser").status_code, 405)

    def test_create_student_signs_in_and_displays_username(self):
        response = self.client.post(
            "/app/createUser",
            {
                "user_name": "boris",
                "email": "boris@school.edu",
                "password": "sk3j5n.k",
                "is_student": "1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "success")
        user = User.objects.get(username="boris")
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertContains(self.client.get("/"), "boris")

    def test_create_instructor_creates_instructor_profile(self):
        response = self.client.post(
            "/app/createUser",
            {
                "user_name": "professor",
                "email": "professor@school.edu",
                "password": "safe-password",
                "is_student": "0",
            },
        )
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username="professor")
        self.assertTrue(InstructorProfile.objects.filter(user=user).exists())

    def test_duplicate_email_returns_400(self):
        User.objects.create_user(
            username="first",
            email="duplicate@school.edu",
            password="password",
        )
        response = self.client.post(
            "/app/createUser",
            {
                "user_name": "second",
                "email": "DUPLICATE@school.edu",
                "password": "password",
                "is_student": "1",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "already in use", status_code=400)

    def test_standard_login_works_and_redirects_home(self):
        User.objects.create_user(
            username="existing",
            email="existing@school.edu",
            password="password123",
        )
        login_page = self.client.get("/accounts/login/")
        self.assertEqual(login_page.status_code, 200)
        self.assertContains(login_page, "csrfmiddlewaretoken")
        response = self.client.post(
            "/accounts/login/",
            {"username": "existing", "password": "password123"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "existing")
