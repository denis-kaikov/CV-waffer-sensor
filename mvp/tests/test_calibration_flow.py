from pathlib import Path

import cv2
import numpy as np

from app.camera.base import Frame
from app.processing.base import OverallResult, SlotState
from app.processing.hybrid import HybridProcessor


def _cassette_image(missing_slot=None):
    height, width = 1200, 1600
    image = np.full((height, width), 220, dtype=np.uint8)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_100)
    marker_size = 150
    positions = {
        10: (60, 60),
        11: (width - 60 - marker_size, 60),
        12: (width - 60 - marker_size, height - 60 - marker_size),
        13: (60, height - 60 - marker_size),
    }
    for marker_id, (x, y) in positions.items():
        marker = cv2.aruco.generateImageMarker(dictionary, marker_id, marker_size)
        image[y : y + marker_size, x : x + marker_size] = marker

    for slot, y in enumerate(np.linspace(285, 915, 25).astype(int)):
        if slot != missing_slot:
            cv2.line(image, (300, y), (1300, y), 40, 3)
    return image


def _processor(tmp_path: Path):
    return HybridProcessor(
        {
            "canonical_size": [1200, 800],
            "calibration_file": str(tmp_path / "calibration.yaml"),
            "model_dir": str(tmp_path / "models"),
            "slot_counts": {100: 25},
            "aruco_type_groups": {10: 100, 20: 150, 30: 200},
            "search_radius": 9,
            "minimum_coverage": 0.45,
            "minimum_score_ratio": 0.45,
            "roi_column_coverage": 0.50,
        }
    )


def test_calibration_is_saved_and_full_cassette_is_ok(tmp_path):
    processor = _processor(tmp_path)
    model = processor.calibrate(
        Frame.now(_cassette_image(), 1, "cassette_left"), 100
    )

    assert len(model["slot_curves_normalized"]) == 25
    assert tmp_path.joinpath("calibration.yaml").exists()
    assert tmp_path.joinpath("models/cassette_left_100.json").exists()
    assert all(0.0 <= value <= 1.0 for value in model["inspection_roi_normalized"])

    result = processor.process(
        Frame.now(_cassette_image(), 2, "cassette_left"), 100
    )
    assert result.overall == OverallResult.OK
    assert result.slots == [SlotState.OCCUPIED_OK] * 25


def test_missing_slot_is_ng(tmp_path):
    processor = _processor(tmp_path)
    processor.calibrate(Frame.now(_cassette_image(), 1, "cassette_left"), 100)

    result = processor.process(
        Frame.now(_cassette_image(missing_slot=12), 2, "cassette_left"), 100
    )
    assert result.overall == OverallResult.NG
    assert result.slots[12] == SlotState.EMPTY
