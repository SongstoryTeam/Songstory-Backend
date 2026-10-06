from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render

from core.forms import ProfileForm, SignUpForm
from core.models import Playlist, Recommendation
from core.ratelimits import IP, rate_limited

AVAILABILITY_CHECKS = {
    "username": lambda value: not User.objects.filter(username__iexact=value).exists(),
    "email": lambda value: not User.objects.filter(email__iexact=value).exists(),
}


@rate_limited("signup", key=IP)
def signup(request):
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Вітаємо! Акаунт створено.")
        return redirect("core:home")
    return render(request, "registration/signup.html", {"form": form})


@rate_limited("signup_check", key=IP, methods=("GET",), json=True)
def check_signup_field(request):
    check = AVAILABILITY_CHECKS.get(request.GET.get("field", ""))
    value = request.GET.get("value", "").strip()
    if check is None or not value:
        return JsonResponse({"available": None})
    return JsonResponse({"available": check(value)})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Профіль оновлено.")
        return redirect("core:profile")

    recommendations = (
        Recommendation.objects.filter(user=request.user)
        .select_related("track", "book", "chapter")
        .order_by("-created_at")
    )
    playlists = Playlist.objects.filter(user=request.user).select_related("book")
    return render(
        request,
        "core/profile.html",
        {
            "form": form,
            "recommendations": recommendations,
            "playlists": playlists,
            "authored_books": request.user.authored_books.all(),
        },
    )
