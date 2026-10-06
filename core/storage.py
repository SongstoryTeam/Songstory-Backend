import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage, storages
from django.utils.deconstruct import deconstructible


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


def get_private_storage():
    return storages["private"]
