from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView

from core import views as core_views
from core.sitemaps import BookSitemap, ChapterSitemap

handler404 = "core.views.page_not_found"
handler500 = "core.views.server_error"

sitemaps = {
    "books": BookSitemap,
    "chapters": ChapterSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("accounts/", include("allauth.urls")),
    path("", include("core.urls")),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="core:home"),
        name="logout",
    ),
    path("signup/", core_views.signup, name="signup"),
    path("robots.txt", core_views.robots_txt, name="robots_txt"),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("sw.js", core_views.service_worker, name="service_worker"),
    path(
        "googlef9b06c02e8f2e7fc.html",
        RedirectView.as_view(url=staticfiles_storage.url("googlef9b06c02e8f2e7fc.html")),
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
