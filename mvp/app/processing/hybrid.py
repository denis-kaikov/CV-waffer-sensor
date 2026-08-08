from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np
import yaml
from scipy.signal import find_peaks

from app.camera.base import Frame
from .base import ImageProcessor, InspectionResult, OverallResult, SlotState


class HybridProcessor(ImageProcessor):
    """ArUco geometry calibration and slot occupancy inspection."""

    DEFAULT_TYPE_GROUPS = {10: 100, 20: 150, 30: 200}

    def __init__(self, config: Optional[dict] = None) -> None:
        config = config or {}
        self.canonical_size = tuple(config.get("canonical_size", (1600, 1200)))
        self.slot_counts = {
            int(key): int(value)
            for key, value in config.get(
                "slot_counts", {100: 25, 150: 25, 200: 25}
            ).items()
        }
        self.type_groups = {
            int(key): int(value)
            for key, value in config.get(
                "aruco_type_groups", self.DEFAULT_TYPE_GROUPS
            ).items()
        }
        self.search_radius = int(config.get("search_radius", 10))
        self.minimum_coverage = float(config.get("minimum_coverage", 0.55))
        self.minimum_score_ratio = float(config.get("minimum_score_ratio", 0.45))
        self.roi_column_coverage = float(config.get("roi_column_coverage", 0.60))
        self.calibration_file = Path(
            config.get("calibration_file", "/app/data/calibration.yaml")
        )
        self.model_dir = Path(config.get("model_dir", "/app/data/models"))
        self.calibrations = self._load_calibrations()
        self.models: Dict[Tuple[str, int], dict] = {}

        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_100)
        self.detector = cv2.aruco.ArucoDetector(dictionary)

    def calibrate(
        self,
        frame: Frame,
        cassette_type_mm: int,
        slot_count: Optional[int] = None,
    ) -> dict:
        """Build and persist a model from a fully occupied cassette."""
        slot_count = int(slot_count or self.slot_counts.get(cassette_type_mm, 25))
        normalized, detected_type, _, _ = self._normalize_by_fiducials(
            frame.image, self.canonical_size
        )
        self._validate_type(detected_type, cassette_type_mm)

        first_pass = self._detect_edges_on_normalized(
            normalized,
            expected_count=slot_count,
            roi=(0.0, 0.0, 1.0, 1.0),
        )
        inspection_roi = self._auto_inspection_roi(first_pass, normalized.shape)
        edges = self._detect_edges_on_normalized(
            normalized,
            expected_count=slot_count,
            roi=inspection_roi,
        )

        _, roi_y1, _, _ = edges["roi_pixels"]
        full_height = normalized.shape[0]
        model = {
            "camera_id": frame.camera_id,
            "cassette_type_mm": int(cassette_type_mm),
            "canonical_size": list(self.canonical_size),
            "inspection_roi_normalized": list(inspection_roi),
            "slot_count": slot_count,
            "slot_curves_normalized": [
                ((curve + roi_y1) / full_height).astype(float).tolist()
                for curve in edges["curves"]
            ],
            "slot_reference_scores": edges["scores"].astype(float).tolist(),
            "minimum_coverage": self.minimum_coverage,
            "minimum_score_ratio": self.minimum_score_ratio,
            "search_radius": self.search_radius,
        }

        model_path = self.model_dir / f"{frame.camera_id}_{cassette_type_mm}.json"
        self._write_json(model_path, model)
        self.models[(frame.camera_id, int(cassette_type_mm))] = model

        camera_cfg = self.calibrations.setdefault(frame.camera_id, {})
        camera_cfg[str(cassette_type_mm)] = {
            "inspection_roi": list(inspection_roi),
            "model_path": str(model_path),
            "slot_count": slot_count,
        }
        self._write_yaml(self.calibration_file, self.calibrations)
        return model

    def process(self, frame: Frame, cassette_type_mm: int) -> InspectionResult:
        if frame.image is None or frame.image.size == 0:
            return InspectionResult(
                OverallResult.ERROR,
                error_code=2001,
                message="Empty frame",
            )

        try:
            model = self._get_model(frame.camera_id, cassette_type_mm)
            normalized, detected_type, _, _ = self._normalize_by_fiducials(
                frame.image, tuple(model["canonical_size"])
            )
            self._validate_type(detected_type, cassette_type_mm)
            slots, diagnostic = self._inspect_with_model(normalized, model)
            overall = (
                OverallResult.OK
                if all(slot == SlotState.OCCUPIED_OK for slot in slots)
                else OverallResult.NG
            )
            return InspectionResult(
                overall=overall,
                slots=slots,
                message=(
                    f"camera={frame.camera_id}; cassette={cassette_type_mm}; "
                    f"occupied={sum(slot == SlotState.OCCUPIED_OK for slot in slots)}/{len(slots)}"
                ),
                diagnostic_image=diagnostic,
            )
        except FileNotFoundError as exc:
            return InspectionResult(
                OverallResult.ERROR,
                error_code=2101,
                message=str(exc),
            )
        except RuntimeError as exc:
            return InspectionResult(
                OverallResult.ERROR,
                error_code=2102,
                message=str(exc),
            )
        except Exception as exc:
            return InspectionResult(
                OverallResult.ERROR,
                error_code=2199,
                message=f"Processing failed: {exc}",
            )

    def _normalize_by_fiducials(
        self,
        image: np.ndarray,
        canonical_size: Sequence[int],
    ) -> Tuple[np.ndarray, int, np.ndarray, np.ndarray]:
        corners, ids, _ = self.detector.detectMarkers(image)
        if ids is None or len(ids) != 4:
            raise RuntimeError("Exactly 4 ArUco markers are required")

        ids = ids.ravel().astype(int)
        groups = ids // 10 * 10
        if len(set(groups.tolist())) != 1 or int(groups[0]) not in self.type_groups:
            raise RuntimeError("ArUco markers do not belong to one cassette type")
        expected_ids = set(range(int(groups[0]), int(groups[0]) + 4))
        if set(ids.tolist()) != expected_ids:
            raise RuntimeError(
                f"Expected marker ids {sorted(expected_ids)}, got {sorted(ids.tolist())}"
            )

        center = np.mean([marker[0].mean(axis=0) for marker in corners], axis=0)
        source = np.float32(
            [
                marker[0][np.argmin(np.linalg.norm(marker[0] - center, axis=1))]
                for marker in corners
            ]
        )
        source_center = source.mean(axis=0)
        source = source[
            np.argsort(np.arctan2(source[:, 1] - source_center[1], source[:, 0] - source_center[0]))
        ]
        source = np.roll(source, -int(np.argmin(source.sum(axis=1))), axis=0)

        width, height = int(canonical_size[0]), int(canonical_size[1])
        destination = np.float32(
            [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]]
        )
        homography = cv2.getPerspectiveTransform(source, destination)
        inverse = np.linalg.inv(homography)
        normalized = cv2.warpPerspective(image, homography, (width, height))
        return normalized, self.type_groups[int(groups[0])], homography, inverse

    def _edge_response(self, image: np.ndarray) -> np.ndarray:
        gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.createCLAHE(2.0, (8, 8)).apply(gray)
        return cv2.GaussianBlur(
            np.abs(
                cv2.Sobel(
                    cv2.GaussianBlur(gray, (5, 5), 0),
                    cv2.CV_32F,
                    0,
                    1,
                    ksize=3,
                )
            ),
            (9, 3),
            0,
        )

    def _detect_edges_on_normalized(
        self,
        normalized: np.ndarray,
        expected_count: int,
        roi: Sequence[float],
    ) -> dict:
        x1, y1, x2, y2 = self._roi_to_pixels(normalized.shape, roi)
        response = self._edge_response(normalized[y1:y2, x1:x2])
        height, width = response.shape
        if height < 3 or width < 3:
            raise RuntimeError("Inspection ROI is too small")

        profile = np.percentile(
            response[:, width // 10 : max(width // 10 + 1, width * 9 // 10)],
            72,
            axis=1,
        ).astype(np.float32)
        profile = cv2.GaussianBlur(profile[:, None], (1, 11), 0).ravel()
        median = float(np.median(profile))
        mad = float(1.4826 * np.median(np.abs(profile - median)) + 1e-6)
        minimum_distance = max(6, height // max(expected_count * 3, 1))

        peaks, properties = find_peaks(
            profile,
            distance=minimum_distance,
            prominence=max(2.5, 1.6 * mad),
        )
        if len(peaks) < expected_count:
            # CLAHE/Sobel scale can vary by source; retry with a softer prominence.
            peaks, properties = find_peaks(
                profile,
                distance=minimum_distance,
                prominence=max(1.0, 0.8 * mad),
            )
        if len(peaks) < expected_count:
            raise RuntimeError(
                f"Found {len(peaks)} front edges, expected {expected_count}"
            )

        selected = self._select_regular_peaks(
            peaks,
            properties["prominences"].astype(np.float32),
            expected_count,
        )
        curves: List[np.ndarray] = []
        strengths: List[np.ndarray] = []
        scores: List[float] = []
        radius = max(8, minimum_distance // 2)

        for seed_y in selected:
            curve, local_strengths = self._track_curve(
                response, int(seed_y), radius
            )
            curves.append(curve)
            strengths.append(local_strengths)
            positive = local_strengths[local_strengths > 0]
            scores.append(float(np.percentile(positive, 55)) if positive.size else 0.0)

        order = np.argsort(selected)
        return {
            "curves": [curves[index] for index in order],
            "strengths": [strengths[index] for index in order],
            "seed_rows": selected[order],
            "scores": np.asarray(scores, np.float32)[order],
            "roi_pixels": (x1, y1, x2, y2),
            "response": response,
            "profile": profile,
        }

    def _track_curve(
        self,
        response: np.ndarray,
        seed_y: int,
        radius: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        height, width = response.shape
        center_x = width // 2
        curve = np.full(width, float(seed_y), np.float32)
        strengths = np.zeros(width, np.float32)
        curve[center_x] = seed_y
        strengths[center_x] = response[seed_y, center_x]

        for direction in (-1, 1):
            previous_y = float(seed_y)
            velocity = 0.0
            x_values = (
                range(center_x - 1, -1, -1)
                if direction < 0
                else range(center_x + 1, width)
            )
            for x in x_values:
                predicted_y = previous_y + velocity
                center_y = int(round(predicted_y))
                candidates = np.arange(
                    max(0, center_y - radius),
                    min(height, center_y + radius + 1),
                )
                if not candidates.size:
                    curve[x] = previous_y
                    continue
                values = response[candidates, x]
                best = int(
                    np.argmax(values - 0.20 * np.abs(candidates - predicted_y))
                )
                current_y = float(candidates[best])
                curve[x] = current_y
                strengths[x] = float(values[best])
                velocity = 0.85 * velocity + 0.15 * (current_y - previous_y)
                previous_y = current_y

        curve = cv2.GaussianBlur(curve[None], (31, 1), 0).ravel()
        return curve, strengths

    def _select_regular_peaks(
        self,
        peaks: np.ndarray,
        strengths: np.ndarray,
        expected_count: int,
    ) -> np.ndarray:
        order = np.argsort(peaks)
        peaks = peaks[order].astype(np.float32)
        strengths = strengths[order].astype(np.float32)
        if len(peaks) == expected_count:
            return peaks.astype(int)

        normalized_strength = strengths / max(float(np.max(strengths)), 1e-6)
        best_cost = float("inf")
        best_indices = None
        count = len(peaks)

        # Try every plausible first/last peak. Between them, each nominal slot
        # is matched to the nearest unused peak. This keeps the selected rows
        # regular while still preferring strong responses.
        for first in range(count - expected_count + 1):
            for last in range(first + expected_count - 1, count):
                pitch = float(peaks[last] - peaks[first]) / (expected_count - 1)
                if pitch <= 0:
                    continue

                indices = [first]
                previous = first
                valid = True
                for slot in range(1, expected_count - 1):
                    target = float(peaks[first]) + pitch * slot
                    minimum = previous + 1
                    maximum = last - (expected_count - 1 - slot)
                    if minimum > maximum:
                        valid = False
                        break
                    candidates = np.arange(minimum, maximum + 1)
                    index = int(candidates[np.argmin(np.abs(peaks[candidates] - target))])
                    if abs(float(peaks[index]) - target) > 0.45 * pitch:
                        valid = False
                        break
                    indices.append(index)
                    previous = index

                if not valid:
                    continue
                indices.append(last)
                selected = peaks[indices]
                spacing = np.diff(selected)
                deviation = float(np.mean(((spacing - pitch) / pitch) ** 2))
                weakness = float(np.mean(1.0 - normalized_strength[indices]))
                cost = deviation + 0.12 * weakness
                if cost < best_cost:
                    best_cost = cost
                    best_indices = indices

        if best_indices is None:
            strongest = np.argsort(strengths)[-expected_count:]
            return np.sort(peaks[strongest]).astype(int)
        return peaks[best_indices].astype(int)

    def _auto_inspection_roi(self, edges: dict, normalized_shape) -> Tuple[float, float, float, float]:
        height, width = normalized_shape[:2]
        roi_x1, roi_y1, _, _ = edges["roi_pixels"]
        curves = np.stack(edges["curves"])
        strengths = np.stack(edges["strengths"])
        response = edges["response"]
        response_median = float(np.median(response))
        noise = response_median + 1.4826 * float(
            np.median(np.abs(response - response_median))
        )

        column_coverage = np.mean(strengths > noise, axis=0)
        valid = column_coverage >= self.roi_column_coverage
        start, end = self._longest_true_run(valid)
        if end - start < max(32, response.shape[1] // 5):
            start, end = response.shape[1] // 10, response.shape[1] * 9 // 10

        x_margin = max(4, int(0.01 * width))
        x1 = max(0, roi_x1 + start - x_margin)
        x2 = min(width, roi_x1 + end + x_margin)

        seed_rows = np.asarray(edges["seed_rows"], np.float32)
        pitch = (
            float(np.median(np.diff(seed_rows)))
            if len(seed_rows) > 1
            else max(8.0, height * 0.02)
        )
        clipped_curves = curves[:, start:end] if end > start else curves
        y1 = max(0, int(np.floor(np.min(clipped_curves) + roi_y1 - 0.60 * pitch)))
        y2 = min(height, int(np.ceil(np.max(clipped_curves) + roi_y1 + 0.60 * pitch)))

        if x2 <= x1 or y2 <= y1:
            raise RuntimeError("Unable to determine inspection ROI")
        return (
            round(x1 / width, 6),
            round(y1 / height, 6),
            round(x2 / width, 6),
            round(y2 / height, 6),
        )

    def _inspect_with_model(self, normalized: np.ndarray, model: dict):
        roi = tuple(model["inspection_roi_normalized"])
        x1, y1, x2, y2 = self._roi_to_pixels(normalized.shape, roi)
        response = self._edge_response(normalized[y1:y2, x1:x2])
        roi_width = response.shape[1]
        full_height = normalized.shape[0]
        search_radius = int(model.get("search_radius", self.search_radius))
        minimum_coverage = float(
            model.get("minimum_coverage", self.minimum_coverage)
        )
        minimum_score_ratio = float(
            model.get("minimum_score_ratio", self.minimum_score_ratio)
        )

        response_median = float(np.median(response))
        local_noise = response_median + 1.4826 * float(
            np.median(np.abs(response - response_median))
        )
        reference_scores = model["slot_reference_scores"]
        slot_states: List[SlotState] = []
        detected_curves: List[np.ndarray] = []

        for slot_index, normalized_curve in enumerate(model["slot_curves_normalized"]):
            nominal = np.asarray(normalized_curve, np.float32) * full_height - y1
            if len(nominal) != roi_width:
                nominal = np.interp(
                    np.linspace(0.0, 1.0, roi_width),
                    np.linspace(0.0, 1.0, len(nominal)),
                    nominal,
                )

            strengths = np.zeros(roi_width, np.float32)
            detected = nominal.astype(np.float32).copy()
            for x in range(roi_width):
                center_y = int(round(float(nominal[x])))
                candidates = np.arange(
                    max(0, center_y - search_radius),
                    min(response.shape[0], center_y + search_radius + 1),
                )
                if not candidates.size:
                    continue
                values = response[candidates, x]
                best = int(
                    np.argmax(values - 0.20 * np.abs(candidates - nominal[x]))
                )
                detected[x] = float(candidates[best])
                strengths[x] = float(values[best])

            positive = strengths[strengths > 0]
            score = float(np.percentile(positive, 55)) if positive.size else 0.0
            coverage = float(
                np.mean(strengths > max(local_noise, 0.45 * score))
            )
            reference_score = max(float(reference_scores[slot_index]), 1e-6)
            occupied = (
                score >= reference_score * minimum_score_ratio
                and coverage >= minimum_coverage
            )
            slot_states.append(
                SlotState.OCCUPIED_OK if occupied else SlotState.EMPTY
            )
            detected_curves.append(detected)

        diagnostic = self._draw_diagnostic(
            normalized,
            (x1, y1, x2, y2),
            detected_curves,
            slot_states,
        )
        return slot_states, diagnostic

    def _draw_diagnostic(
        self,
        normalized: np.ndarray,
        roi_pixels: Tuple[int, int, int, int],
        curves: List[np.ndarray],
        states: List[SlotState],
    ) -> np.ndarray:
        diagnostic = (
            cv2.cvtColor(normalized, cv2.COLOR_GRAY2BGR)
            if normalized.ndim == 2
            else normalized.copy()
        )
        x1, y1, x2, y2 = roi_pixels
        cv2.rectangle(diagnostic, (x1, y1), (x2 - 1, y2 - 1), (255, 255, 0), 2)
        for slot_index, (curve, state) in enumerate(zip(curves, states)):
            color = (0, 255, 0) if state == SlotState.OCCUPIED_OK else (0, 0, 255)
            points = np.column_stack(
                (
                    np.arange(len(curve), dtype=np.int32) + x1,
                    np.rint(curve).astype(np.int32) + y1,
                )
            )
            cv2.polylines(diagnostic, [points], False, color, 1)
            midpoint = points[len(points) // 2]
            cv2.putText(
                diagnostic,
                str(slot_index),
                (int(midpoint[0]) + 4, int(midpoint[1]) - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                color,
                1,
                cv2.LINE_AA,
            )
        return diagnostic

    def _validate_type(self, detected_type: int, requested_type: int) -> None:
        if int(detected_type) != int(requested_type):
            raise RuntimeError(
                f"Cassette type mismatch: ArUco={detected_type}, requested={requested_type}"
            )

    def _get_model(self, camera_id: str, cassette_type_mm: int) -> dict:
        key = (camera_id, int(cassette_type_mm))
        if key in self.models:
            return self.models[key]

        camera_cfg = self.calibrations.get(camera_id, {})
        entry = camera_cfg.get(str(cassette_type_mm))
        if not entry:
            raise FileNotFoundError(
                f"No calibration for camera={camera_id}, cassette={cassette_type_mm}"
            )
        path = Path(entry["model_path"])
        if not path.exists():
            raise FileNotFoundError(f"Calibration model does not exist: {path}")
        model = json.loads(path.read_text(encoding="utf-8"))
        self.models[key] = model
        return model

    def _load_calibrations(self) -> dict:
        if not self.calibration_file.exists():
            return {}
        data = yaml.safe_load(self.calibration_file.read_text(encoding="utf-8"))
        return data or {}

    @staticmethod
    def _roi_to_pixels(shape, roi: Sequence[float]) -> Tuple[int, int, int, int]:
        height, width = shape[:2]
        x1 = max(0, min(width - 1, int(round(width * float(roi[0])))))
        y1 = max(0, min(height - 1, int(round(height * float(roi[1])))))
        x2 = max(x1 + 1, min(width, int(round(width * float(roi[2])))))
        y2 = max(y1 + 1, min(height, int(round(height * float(roi[3])))))
        return x1, y1, x2, y2

    @staticmethod
    def _longest_true_run(values: np.ndarray) -> Tuple[int, int]:
        best_start = best_end = start = 0
        for index, value in enumerate(np.r_[values, False]):
            if value:
                if index == 0 or not values[index - 1]:
                    start = index
            elif index > start and index - start > best_end - best_start:
                best_start, best_end = start, index
        return best_start, best_end

    @staticmethod
    def _write_json(path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(path)

    @staticmethod
    def _write_yaml(path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            yaml.safe_dump(value, allow_unicode=True, sort_keys=True),
            encoding="utf-8",
        )
        temporary.replace(path)
