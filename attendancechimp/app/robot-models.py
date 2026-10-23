# LLM: ChatGPT (OpenAI GPT-5)
# Prompt: "Generate a simple Django models.py for AttendanceChimp. Use separate
# InstructorProfile and StudentProfile tables tied to Django users; a Course with
# name, instructor, and meeting schedule; an explicit Enrollment many-to-many
# join; a Lecture with a date and QR identifier; and a QRCodeUpload linked to a
# student and optionally a lecture. Favor a concise implementation and include
# readable __str__ methods."

"""Concise LLM-generated alternative model used only for comparison."""

from django.contrib.auth.models import User
from django.db import models


class InstructorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.user.username


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.user.username


class Course(models.Model):
    name = models.CharField(max_length=200)
    instructor = models.ForeignKey(InstructorProfile, on_delete=models.CASCADE)
    meeting_schedule = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Enrollment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)


class Lecture(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateTimeField()
    qr_identifier = models.CharField(max_length=100)


class QRCodeUpload(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    image = models.FileField(upload_to="qr_uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)


