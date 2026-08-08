from __future__ import annotations

import argparse
import logging
import os

import cv2

from app.camera.base import Frame
from app.camera.manager import CameraManager
from app.configuration import build_camera_config, load_config
from app.processing.hybrid import HybridProcessor


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate cassette geometry")
    parser.add_argument("--camera", required=True, help="Camera id from config.yaml")
    parser.add_argument("--cassette", required=True, type=int, choices=(100, 150, 200))
    parser.add_argument("--image", help="Optional image path instead of live camera capture")
    parser.add_argument(
        "--config",
        default=os.getenv("KMZ_CONFIG", "/app/config/config.yaml"),
    )
    args = parser.parse_args()

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    cfg = load_config(args.config)
    processor = HybridProcessor(cfg.get("processing", {}))

    if args.image:
        image = cv2.imread(args.image, cv2.IMREAD_UNCHANGED)
        if image is None:
            raise RuntimeError(f"Unable to read calibration image: {args.image}")
        frame = Frame.now(image, 0, args.camera)
    else:
        camera_cfg = cfg["cameras"][args.camera]
        cameras = CameraManager()
        cameras.add(camera_cfg["driver"], build_camera_config(args.camera, camera_cfg))
        cameras.connect_all()
        try:
            frame = cameras.capture(args.camera)
        finally:
            cameras.disconnect_all()

    model = processor.calibrate(frame, args.cassette)
    print(
        f"Calibrated camera={args.camera}, cassette={args.cassette}, "
        f"roi={model['inspection_roi_normalized']}, slots={model['slot_count']}"
    )


if __name__ == "__main__":
    main()
