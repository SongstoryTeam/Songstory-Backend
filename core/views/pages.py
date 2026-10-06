from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.static import serve


def robots_txt(request):
    return HttpResponse(render_to_string("robots.txt", request=request), content_type="text/plain")


def service_worker(request):
    response = serve(request, "sw.js", document_root=settings.BASE_DIR / "static")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response


def offline(request):
    return render(request, "offline.html")


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)


def too_many_requests(request, exception=None):
    return render(request, "429.html", status=429)
