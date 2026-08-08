from __future__ import annotations

from pathlib import Path
import yaml

from app.camera.base import CameraConfig


def load_config(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def build_camera_config(camera_id: str, data: dict) -> CameraConfig:
    known = {"driver", "serial_number", "exposure_us", "gain_db", "timeout_ms", "pixel_format"}
    extra = {k: v for k, v in data.items() if k not in known}
    return CameraConfig(
        camera_id=camera_id,
        serial_number=str(data.get("serial_number", "")),
        exposure_us=float(data.get("exposure_us", 15000)),
        gain_db=float(data.get("gain_db", 0)),
        timeout_ms=int(data.get("timeout_ms", 3000)),
        pixel_format=str(data.get("pixel_format", "mono8")),
        extra=extra,
    )
