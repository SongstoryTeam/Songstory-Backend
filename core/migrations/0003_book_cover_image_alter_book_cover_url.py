from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_alter_book_options_book_cover_url_book_created_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="cover_image",
            field=models.ImageField(blank=True, null=True, upload_to="books/covers/", verbose_name="Файл обкладинки"),
        ),
        migrations.AlterField(
            model_name="book",
            name="cover_url",
            field=models.URLField(blank=True, verbose_name="Посилання на обкладинку (запасне)"),
        ),
    ]
