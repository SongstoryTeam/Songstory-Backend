from django.conf import settings
from django.core.exceptions import ValidationError


def validate_upload_size(file) -> None:
    if file.size > settings.VERIFICATION_UPLOAD_MAX_BYTES:
        limit_mb = settings.VERIFICATION_UPLOAD_MAX_BYTES // (1024 * 1024)
        raise ValidationError(f"Файл завеликий. Максимальний розмір — {limit_mb} МБ.")
