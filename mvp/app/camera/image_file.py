from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2

from .base import Camera, CameraConfig, CameraError, CameraState, Frame


class ImageFileCamera(Camera):
    def __init__(self) -> None:
        self._config: CameraConfig | None = None
        self._path: Path | None = None
        self._state = CameraState.DISCONNECTED
        self._last_error: Optional[str] = None
        self._frame_id = 0

    def configure(self, config: CameraConfig) -> None:
        self._config = config
        path = (config.extra or {}).get("path")
        if not path:
            raise CameraError("image_file driver requires extra.path")
        self._path = Path(path)

    def connect(self) -> None:
        if self._path is None or not self._path.exists():
            raise CameraError(f"Test image does not exist: {self._path}")
        self._state = CameraState.IDLE

    def disconnect(self) -> None:
        self._state = CameraState.DISCONNECTED

    def capture(self) -> Frame:
        if self._config is None or self._path is None:
            raise CameraError("Image-file camera is not configured")
        image = cv2.imread(str(self._path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise CameraError(f"Unable to read image: {self._path}")
        self._frame_id += 1
        return Frame.now(image, self._frame_id, self._config.camera_id)

    def state(self) -> CameraState:
        return self._state

    def last_error(self) -> Optional[str]:
        return self._last_error
