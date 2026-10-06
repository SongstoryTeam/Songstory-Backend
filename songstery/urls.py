from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import include, path
from django.views.generic.base import RedirectView

from core.sitemaps import BookSitemap, ChapterSitemap, StaticViewSitemap
from core.views import accounts, pages

handler404 = "core.views.pages.page_not_found"
handler500 = "core.views.pages.server_error"

sitemaps = {
    "static": StaticViewSitemap,
    "books": BookSitemap,
    "chapters": ChapterSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="core:home"), name="logout"),
    path("signup/", accounts.signup, name="signup"),
    path("signup/check/", accounts.check_signup_field, name="signup_check"),
    path("robots.txt", pages.robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("sw.js", pages.service_worker, name="service_worker"),
    path("offline/", pages.offline, name="offline"),
    path(
        "googlef9b06c02e8f2e7fc.html",
        RedirectView.as_view(url=staticfiles_storage.url("googlef9b06c02e8f2e7fc.html")),
    ),
    path("", include("core.urls")),
]
