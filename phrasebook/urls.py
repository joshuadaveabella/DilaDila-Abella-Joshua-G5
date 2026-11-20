from django.urls import path

from . import views

app_name = "phrasebook"

urlpatterns = [
    path("", views.my_phrasebook, name="my_phrasebook"),
    path("new/", views.entry_create, name="entry_create"),
    path("<int:pk>/edit/", views.entry_update, name="entry_update"),
    path("<int:pk>/delete/", views.entry_delete, name="entry_delete"),
    path("save/<int:phrase_pk>/", views.save_from_library, name="save_from_library"),
    path("all/", views.all_phrasebooks, name="all_phrasebooks"),  # admin, read-only
]
