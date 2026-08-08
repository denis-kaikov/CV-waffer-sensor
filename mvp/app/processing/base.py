from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum

import numpy as np

from app.camera.base import Frame


class OverallResult(IntEnum):
    NONE = 0
    OK = 1
    NG = 2
    ERROR = 3


class SlotState(IntEnum):
    EMPTY = 0
    OCCUPIED_OK = 1
    CROSS_SLOT = 2
    SHIFTED_IN_SLOT = 3
    DOUBLE_LOADED_SUSPECT = 4
    UNCERTAIN = 5


@dataclass
class InspectionResult:
    overall: OverallResult
    slots: list[SlotState] = field(default_factory=list)
    error_code: int = 0
    message: str = ""
    diagnostic_image: np.ndarray | None = None


class ImageProcessor(ABC):
    @abstractmethod
    def process(self, frame: Frame, cassette_type_mm: int) -> InspectionResult: ...
