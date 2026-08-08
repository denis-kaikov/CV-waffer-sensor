from __future__ import annotations

from dataclasses import dataclass
import threading

from .base import Camera, CameraConfig, Frame
from .factory import create_camera


@dataclass
class CameraEntry:
    camera: Camera
    lock: threading.Lock


class CameraManager:
    def __init__(self) -> None:
        self._cameras: dict[str, CameraEntry] = {}

    def add(self, driver: str, config: CameraConfig) -> None:
        camera = create_camera(driver)
        camera.configure(config)
        self._cameras[config.camera_id] = CameraEntry(camera=camera, lock=threading.Lock())

    def connect_all(self) -> None:
        for entry in self._cameras.values():
            entry.camera.connect()

    def disconnect_all(self) -> None:
        for entry in self._cameras.values():
            entry.camera.disconnect()

    def capture(self, camera_id: str) -> Frame:
        entry = self._cameras[camera_id]
        with entry.lock:
            return entry.camera.capture()

    def statuses(self) -> dict[str, str]:
        return {camera_id: entry.camera.state().value for camera_id, entry in self._cameras.items()}
