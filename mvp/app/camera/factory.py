from .base import Camera
from .daheng import DahengCamera
from .image_file import ImageFileCamera
from .mock import MockCamera


def create_camera(driver: str) -> Camera:
    drivers = {
        "daheng": DahengCamera,
        "mock": MockCamera,
        "image_file": ImageFileCamera,
    }
    try:
        return drivers[driver.lower()]()
    except KeyError as exc:
        raise ValueError(f"Unsupported camera driver: {driver}") from exc
