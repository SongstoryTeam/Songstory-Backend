from django.db import migrations


def forward(apps, schema_editor):
    Book = apps.get_model("core", "Book")
    BookTranslation = apps.get_model("core", "BookTranslation")
    Chapter = apps.get_model("core", "Chapter")
    ChapterTranslation = apps.get_model("core", "ChapterTranslation")
    Language = apps.get_model("core", "Language")

    uk = Language.objects.get(code="uk")

    for book in Book.objects.all():
        BookTranslation.objects.get_or_create(
            book=book,
            language=uk,
            defaults={"title": book.title or "", "description": book.description or ""},
        )

    for chapter in Chapter.objects.all():
        ChapterTranslation.objects.get_or_create(
            chapter=chapter,
            language=uk,
            defaults={
                "title": chapter.title or "",
                "description": chapter.description or "",
                "mood_tags": chapter.mood_tags or "",
            },
        )


def reverse(apps, schema_editor):
    apps.get_model("core", "BookTranslation").objects.all().delete()
    apps.get_model("core", "ChapterTranslation").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0016_book_chapter_translations"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
