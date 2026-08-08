from __future__ import annotations

from typing import Optional
import threading

import numpy as np

from .base import Camera, CameraConfig, CameraError, CameraState, Frame


class DahengCamera(Camera):
    """Adapter over the Daheng Galaxy Python SDK (gxipy).

    All gxipy-specific code is intentionally kept in this module.
    """

    def __init__(self) -> None:
        self._config: CameraConfig | None = None
        self._device_manager = None
        self._device = None
        self._state = CameraState.DISCONNECTED
        self._last_error: Optional[str] = None
        self._frame_id = 0
        self._lock = threading.Lock()

    def _gx(self):
        try:
            import gxipy as gx  # type: ignore
            return gx
        except ImportError as exc:
            raise CameraError("gxipy is not installed; install Daheng Galaxy Python SDK") from exc

    def configure(self, config: CameraConfig) -> None:
        self._config = config
        if self._device is not None:
            self._apply_configuration()

    def connect(self) -> None:
        if self._config is None:
            raise CameraError("Camera is not configured")
        gx = self._gx()
        try:
            self._device_manager = gx.DeviceManager()
            count, info_list = self._device_manager.update_device_list()
            if count == 0:
                raise CameraError("No Daheng cameras found")

            serial = self._config.serial_number
            if serial:
                self._device = self._device_manager.open_device_by_sn(serial)
            else:
                self._device = self._device_manager.open_device_by_index(1)

            self._apply_configuration()
            self._device.stream_on()
            self._state = CameraState.IDLE
            self._last_error = None
        except Exception as exc:
            self._state = CameraState.ERROR
            self._last_error = str(exc)
            self.disconnect()
            raise CameraError(f"Failed to connect Daheng camera: {exc}") from exc

    def _apply_configuration(self) -> None:
        if self._device is None or self._config is None:
            return
        gx = self._gx()
        cfg = self._config
        try:
            if cfg.pixel_format.lower() == "mono8" and self._device.PixelFormat.is_implemented():
                self._device.PixelFormat.set(gx.GxPixelFormatEntry.MONO8)
            if self._device.ExposureTime.is_implemented():
                self._device.ExposureTime.set(cfg.exposure_us)
            if self._device.Gain.is_implemented():
                self._device.Gain.set(cfg.gain_db)
            if self._device.TriggerMode.is_implemented():
                self._device.TriggerMode.set(gx.GxSwitchEntry.ON)
            if self._device.TriggerSource.is_implemented():
                self._device.TriggerSource.set(gx.GxTriggerSourceEntry.SOFTWARE)
        except Exception as exc:
            raise CameraError(f"Failed to configure Daheng camera: {exc}") from exc

    def capture(self) -> Frame:
        if self._device is None or self._config is None:
            raise CameraError("Camera is not connected")
        with self._lock:
            try:
                self._state = CameraState.STREAMING
                if self._device.TriggerSoftware.is_implemented():
                    self._device.TriggerSoftware.send_command()
                raw = self._device.data_stream[0].get_image(self._config.timeout_ms)
                if raw is None:
                    raise CameraError("Camera timeout: no frame received")
                if raw.get_status() != 0:
                    raise CameraError(f"Invalid frame status: {raw.get_status()}")
                image = raw.get_numpy_array()
                if image is None:
                    raise CameraError("SDK returned an empty frame")
                self._frame_id += 1
                self._state = CameraState.IDLE
                return Frame.now(np.array(image, copy=True), self._frame_id, self._config.camera_id)
            except Exception as exc:
                self._state = CameraState.ERROR
                self._last_error = str(exc)
                raise CameraError(f"Daheng capture failed: {exc}") from exc

    def disconnect(self) -> None:
        try:
            if self._device is not None:
                try:
                    self._device.stream_off()
                except Exception:
                    pass
                self._device.close_device()
        finally:
            self._device = None
            self._device_manager = None
            if self._state != CameraState.ERROR:
                self._state = CameraState.DISCONNECTED

    def state(self) -> CameraState:
        return self._state

    def last_error(self) -> Optional[str]:
        return self._last_error
