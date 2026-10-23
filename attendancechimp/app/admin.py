from django.contrib import admin

from .models import (
    Course,
    Enrollment,
    InstructorProfile,
    Lecture,
    QRCodeUpload,
    StudentProfile,
)

admin.site.register(InstructorProfile)
admin.site.register(StudentProfile)
admin.site.register(Course)
admin.site.register(Enrollment)
admin.site.register(Lecture)
admin.site.register(QRCodeUpload)
