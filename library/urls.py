from django.urls import path

from . import views

app_name = "library"

urlpatterns = [
    path("", views.phrase_list, name="phrase_list"),
    # Admin only
    path("manage/", views.manage_phrases, name="manage_phrases"),
    path("manage/phrases/new/", views.phrase_create, name="phrase_create"),
    path("manage/phrases/<int:pk>/edit/", views.phrase_update, name="phrase_update"),
    path("manage/phrases/<int:pk>/delete/", views.phrase_delete, name="phrase_delete"),
    path("manage/phrases/<int:pk>/toggle/", views.phrase_toggle, name="phrase_toggle"),
    path("manage/categories/", views.manage_categories, name="manage_categories"),
    path("manage/categories/new/", views.category_create, name="category_create"),
    path("manage/categories/<int:pk>/edit/", views.category_update, name="category_update"),
    path("manage/categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
]
