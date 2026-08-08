from __future__ import annotations

from typing import Optional
import numpy as np

from .base import Camera, CameraConfig, CameraState, Frame


class MockCamera(Camera):
    def __init__(self) -> None:
        self._config: CameraConfig | None = None
        self._state = CameraState.DISCONNECTED
        self._frame_id = 0

    def configure(self, config: CameraConfig) -> None:
        self._config = config

    def connect(self) -> None:
        self._state = CameraState.IDLE

    def disconnect(self) -> None:
        self._state = CameraState.DISCONNECTED

    def capture(self) -> Frame:
        if self._config is None:
            raise RuntimeError("Mock camera is not configured")
        self._frame_id += 1
        image = np.zeros((3036, 4024), dtype=np.uint8)
        return Frame.now(image, self._frame_id, self._config.camera_id)

    def state(self) -> CameraState:
        return self._state

    def last_error(self) -> Optional[str]:
        return None
