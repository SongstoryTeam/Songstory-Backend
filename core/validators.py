from django.conf import settings
from django.core.exceptions import ValidationError

BYTES_PER_MEGABYTE = 1024 * 1024


def validate_upload_size(file) -> None:
    if file.size > settings.VERIFICATION_UPLOAD_MAX_BYTES:
        limit_mb = settings.VERIFICATION_UPLOAD_MAX_BYTES // BYTES_PER_MEGABYTE
        raise ValidationError(f"Файл завеликий. Максимальний розмір — {limit_mb} МБ.")
