from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts import views as account_views

urlpatterns = [
    path("", account_views.home, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("library/", include("library.urls")),
    path("phrasebook/", include("phrasebook.urls")),
]

if settings.DEBUG:
    # Development only: in production the web server must serve /media/
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "accounts.views.permission_denied"
