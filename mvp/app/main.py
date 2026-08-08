from __future__ import annotations

import asyncio
import logging
import os

from app.application.controller import InspectionController
from app.camera.manager import CameraManager
from app.configuration import build_camera_config, load_config
from app.modbus.server import run_modbus_server
from app.processing.hybrid import HybridProcessor


async def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    config_path = os.getenv("KMZ_CONFIG", "/app/config/config.yaml")
    cfg = load_config(config_path)

    cameras = CameraManager()
    for camera_id, camera_cfg in cfg["cameras"].items():
        cameras.add(camera_cfg["driver"], build_camera_config(camera_id, camera_cfg))

    controller = InspectionController(cameras, HybridProcessor(cfg.get("processing", {})))
    controller.initialize()

    modbus_cfg = cfg.get("modbus", {})
    await run_modbus_server(
        controller,
        list(cfg["cameras"].keys()),
        str(modbus_cfg.get("host", "0.0.0.0")),
        int(modbus_cfg.get("port", 1502)),
    )


if __name__ == "__main__":
    asyncio.run(main())
