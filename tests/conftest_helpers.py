from django.contrib.auth.models import User

from core.models import Author, Book, Chapter, Platform, Track


def make_user(username: str = "reader", **extra) -> User:
    return User.objects.create_user(username, f"{username}@example.com", "pass-12345", **extra)


def make_book(user: User | None = None, title: str = "Кобзар", author: str = "Тарас Шевченко", approved: bool = True) -> Book:
    return Book.objects.create(
        title=title,
        author=Author.objects.get_or_create(name=author)[0],
        year=1840,
        creator=user,
        is_approved=approved,
    )


def make_chapter(book: Book, number: int = 1) -> Chapter:
    return Chapter.objects.create(book=book, number=number)


def make_track(external_id: str = "dQw4w9WgXcQ", platform: str = Platform.YOUTUBE, title: str = "Трек") -> Track:
    return Track.objects.create(platform=platform, external_id=external_id, title=title, artist="Виконавець")
