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
]
