from __future__ import annotations

from dataclasses import dataclass
import threading
import time

from app.camera.manager import CameraManager
from app.processing.base import InspectionResult, OverallResult
from app.processing.hybrid import HybridProcessor
from .state_machine import SystemState


@dataclass
class ControlCommand:
    command_id: int
    camera_id: str
    cassette_type_mm: int
    dataset_mode: bool = False


class InspectionController:
    def __init__(self, cameras: CameraManager, processor: HybridProcessor) -> None:
        self.cameras = cameras
        self.processor = processor
        self.state = SystemState.INITIALIZING
        self.last_command_id = 0
        self.last_result = InspectionResult(OverallResult.NONE)
        self.processing_time_ms = 0
        self._lock = threading.Lock()

    def initialize(self) -> None:
        self.cameras.connect_all()
        self.state = SystemState.READY

    def inspect(self, command: ControlCommand) -> InspectionResult:
        with self._lock:
            if self.state != SystemState.READY:
                return InspectionResult(OverallResult.ERROR, error_code=1001, message="System is not ready")
            if command.command_id == self.last_command_id:
                return self.last_result

            started = time.perf_counter()
            try:
                self.state = SystemState.CAPTURING
                frame = self.cameras.capture(command.camera_id)
                self.state = SystemState.PROCESSING
                result = self.processor.process(frame, command.cassette_type_mm)
                self.last_command_id = command.command_id
                self.last_result = result
                self.processing_time_ms = int((time.perf_counter() - started) * 1000)
                self.state = SystemState.RESULT_READY
                return result
            except Exception as exc:
                self.last_result = InspectionResult(OverallResult.ERROR, error_code=1002, message=str(exc))
                self.processing_time_ms = int((time.perf_counter() - started) * 1000)
                self.state = SystemState.ERROR
                return self.last_result

    def acknowledge(self) -> None:
        if self.state == SystemState.RESULT_READY:
            self.state = SystemState.READY

    def reset_error(self) -> None:
        if self.state == SystemState.ERROR:
            self.state = SystemState.READY
