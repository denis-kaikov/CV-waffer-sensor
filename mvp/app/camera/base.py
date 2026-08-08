from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import time

import numpy as np


class CameraState(str, Enum):
    DISCONNECTED = "disconnected"
    IDLE = "idle"
    STREAMING = "streaming"
    ERROR = "error"


@dataclass(frozen=True)
class CameraConfig:
    camera_id: str
    serial_number: str = ""
    exposure_us: float = 15000.0
    gain_db: float = 0.0
    timeout_ms: int = 3000
    pixel_format: str = "mono8"
    extra: dict | None = None


@dataclass
class Frame:
    image: np.ndarray
    frame_id: int
    timestamp_ns: int
    camera_id: str

    @classmethod
    def now(cls, image: np.ndarray, frame_id: int, camera_id: str) -> "Frame":
        return cls(image=image, frame_id=frame_id, timestamp_ns=time.time_ns(), camera_id=camera_id)


class CameraError(RuntimeError):
    pass


class Camera(ABC):
    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def configure(self, config: CameraConfig) -> None: ...

    @abstractmethod
    def capture(self) -> Frame: ...

    @abstractmethod
    def state(self) -> CameraState: ...

    @abstractmethod
    def last_error(self) -> Optional[str]: ...
