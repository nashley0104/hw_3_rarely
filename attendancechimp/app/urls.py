from django.urls import path

from . import views

urlpatterns = [
    # HW2
    path("time", views.time_view, name="time"),
    path("sum", views.sum_view, name="sum"),
    # HW4
    path("", views.index, name="home"),
    path("index.html", views.index, name="index_html"),
    path("new", views.new_user, name="new_user"),
    path("new/", views.new_user),
    path("createUser", views.createUser, name="create_user"),
    path("createUser/", views.createUser),
    path("api/createUser/", views.createUser, name="create_user_api"),
    # HW5 forms
    path("new_course", views.new_course, name="new_course"),
    path("new_course/", views.new_course),
    path("new_lecture", views.new_lecture, name="new_lecture"),
    path("new_lecture/", views.new_lecture),
    path("new_qr_upload", views.new_qr_upload, name="new_qr_upload"),
    path("new_qr_upload/", views.new_qr_upload),
    # HW5 role-protected endpoints
    path("createCourse", views.createCourse, name="create_course"),
    path("createCourse/", views.createCourse),
    path("createLecture", views.createLecture, name="create_lecture"),
    path("createLecture/", views.createLecture),
    path("createQRCodeUpload", views.createQRCodeUpload, name="create_qr_upload"),
    path("createQRCodeUpload/", views.createQRCodeUpload),
    path("dumpUploads", views.dumpUploads, name="dump_uploads"),
    path("dumpUploads/", views.dumpUploads),
]
