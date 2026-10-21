from http import HTTPStatus

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

SERVICE_WORKER_TEMPLATE = "pwa/sw.js"
MANIFEST_TEMPLATE = "pwa/manifest.json"
JAVASCRIPT_CONTENT_TYPE = "text/javascript"
MANIFEST_CONTENT_TYPE = "application/manifest+json"
PLAIN_TEXT_CONTENT_TYPE = "text/plain"
SERVICE_WORKER_SCOPE = "/"
NO_CACHE = "no-cache"


def robots_txt(request):
    return HttpResponse(render_to_string("robots.txt", request=request), content_type=PLAIN_TEXT_CONTENT_TYPE)


def service_worker(request):
    response = render(request, SERVICE_WORKER_TEMPLATE, content_type=JAVASCRIPT_CONTENT_TYPE)
    response["Service-Worker-Allowed"] = SERVICE_WORKER_SCOPE
    response["Cache-Control"] = NO_CACHE
    return response


def manifest(request):
    return render(request, MANIFEST_TEMPLATE, content_type=MANIFEST_CONTENT_TYPE)


def offline(request):
    return render(request, "offline.html")


def page_not_found(request, exception):
    return render(request, "404.html", status=HTTPStatus.NOT_FOUND)


def server_error(request):
    return render(request, "500.html", status=HTTPStatus.INTERNAL_SERVER_ERROR)


def too_many_requests(request, exception=None):
    return render(request, "429.html", status=HTTPStatus.TOO_MANY_REQUESTS)
