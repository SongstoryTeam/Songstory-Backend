import logging
import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage, storages
from django.utils.deconstruct import deconstructible
from whitenoise.storage import CompressedManifestStaticFilesStorage

logger = logging.getLogger(__name__)


@deconstructible
class PrivateMediaStorage(FileSystemStorage):
    @property
    def base_location(self) -> str:
        return str(settings.PRIVATE_MEDIA_ROOT)

    @property
    def location(self) -> str:
        return os.path.abspath(self.base_location)

    @property
    def base_url(self) -> None:
        return None


class TolerantManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Manifest-сховище, яке не валить сторінку через відсутній статичний файл.

    Стандартне поведінка — ValueError (HTTP 500 разом із сторінкою 500, бо вона
    теж наслідує base.html). Тут пишемо попередження в лог і віддаємо URL без хеша.
    """

    manifest_strict = False

    def stored_name(self, name):
        try:
            return super().stored_name(name)
        except ValueError:
            logger.warning("Static file is missing, serving unhashed URL: %s", name)
            return name


def get_private_storage():
    return storages["private"]
