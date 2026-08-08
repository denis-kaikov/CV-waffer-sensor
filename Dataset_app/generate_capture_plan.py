from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


NORMAL_SCENARIO_COUNTS = {
    "empty_cassette": 5,
    "full_cassette": 5,
    "full_minus_one": 25,
    "single_plate": 25,
    "sparse_fill": 800,
    "medium_fill": 1300,
    "dense_fill": 450,
    "adjacent_group": 650,
    "separated_groups": 500,
    "zone_fill": 250,
    "alternating": 350,
    "production_mix": 640,
}

SHIFTED_SCENARIO_COUNTS = {
    "shifted_single": 25,
    "shifted_full_minus_one": 25,
    "shifted_sparse": 200,
    "shifted_medium": 350,
    "shifted_dense": 150,
    "shifted_adjacent_group": 150,
    "shifted_separated_groups": 75,
    "shifted_double": 25,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate capture_plan.json for CassetteDatasetCapture.")
    parser.add_argument("--output-path", default="capture_plan.generated.json")
    parser.add_argument("--project", default="")
    parser.add_argument("--cassette-size-mm", type=int, default=150)
    parser.add_argument("--slot-count", type=int, default=25)
    parser.add_argument("--shots-per-config", type=int, default=1)
    parser.add_argument("--default-exposure-us", type=float, default=8000)
    parser.add_argument("--default-gain", type=float, default=0)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


class PlanGenerator:
    def __init__(
        self,
        *,
        project: str,
        cassette_size_mm: int,
        slot_count: int,
        shots_per_config: int,
        default_exposure_us: float,
        default_gain: float,
        seed: int,
    ) -> None:
        if slot_count <= 0:
            raise ValueError("slot_count must be greater than zero.")
        if shots_per_config <= 0:
            raise ValueError("shots_per_config must be greater than zero.")

        self.project = project or f"cassette_{cassette_size_mm}mm_dataset_v1"
        self.cassette_size_mm = cassette_size_mm
        self.slot_count = slot_count
        self.shots_per_config = shots_per_config
        self.default_exposure_us = default_exposure_us
        self.default_gain = default_gain
        self.rng = random.Random(seed)
        self.all_slots = list(range(1, slot_count + 1))
        self.slot_width = max(2, len(str(slot_count)))
        self.configs: list[dict] = []
        self.scenario_summary: list[tuple[str, int]] = []

    def format_slot_list(self, slots: list[int]) -> str:
        if not slots:
            return "нет слотов"
        return ", ".join(str(slot) for slot in sorted(slots))

    def zone_slots(self, zone: str) -> list[int]:
        upper_end = -(-self.slot_count // 3)
        middle_end = -(-(self.slot_count * 2) // 3)
        if zone == "upper":
            return list(range(1, upper_end + 1))
        if zone == "middle":
            start = min(upper_end + 1, self.slot_count)
            end = max(start, middle_end)
            return list(range(start, end + 1))
        if zone == "lower":
            start = min(middle_end + 1, self.slot_count)
            return list(range(start, self.slot_count + 1))
        raise ValueError(f"Unsupported zone: {zone}")

    def random_distinct_slots(self, count: int, candidates: list[int]) -> list[int]:
        if count <= 0:
            return []
        if count > len(candidates):
            raise ValueError(f"Cannot pick {count} slots from {len(candidates)} candidates.")
        return sorted(self.rng.sample(candidates, count))

    def range_count(self, min_value: int, max_value: int, *, allow_full: bool = False) -> int:
        max_allowed = self.slot_count if allow_full else max(1, self.slot_count - 1)
        effective_max = min(max_value, max_allowed)
        effective_min = min(min_value, effective_max)
        return self.rng.randint(effective_min, effective_max)

    def mask_from_assignments(self, assignments: dict[int, str]) -> str:
        values = ["0"] * self.slot_count
        for slot, value in assignments.items():
            if slot < 1 or slot > self.slot_count:
                raise ValueError(f"Slot {slot} is out of range 1..{self.slot_count}.")
            values[slot - 1] = value
        return "".join(values)

    def make_normal_definition(self, name: str, normal_slots: list[int], instruction: str) -> dict:
        normal_assignments = {slot: "1" for slot in normal_slots}
        return {
            "name": name,
            "normal_occupancy": self.mask_from_assignments(normal_assignments),
            "blocked_slots": self.mask_from_assignments(normal_assignments),
            "slot_states": self.mask_from_assignments(normal_assignments),
            "anomalies": [],
            "operator_instruction": instruction,
        }

    def make_shifted_definition(
        self,
        name: str,
        shifted_slot: int,
        normal_slots: list[int],
        instruction: str,
        note: str,
        severity: int = 1,
    ) -> dict:
        if shifted_slot in normal_slots:
            raise ValueError("Shifted slot cannot also be a normal slot.")

        normal_assignments = {slot: "1" for slot in normal_slots}
        blocked_assignments = {slot: "1" for slot in normal_slots}
        state_assignments = {slot: "1" for slot in normal_slots}
        blocked_assignments[shifted_slot] = "1"
        state_assignments[shifted_slot] = "3"

        return {
            "name": name,
            "normal_occupancy": self.mask_from_assignments(normal_assignments),
            "blocked_slots": self.mask_from_assignments(blocked_assignments),
            "slot_states": self.mask_from_assignments(state_assignments),
            "anomalies": [
                {
                    "type": "shifted_in_slot_plate",
                    "slots": [shifted_slot],
                    "severity": severity,
                    "note": note,
                }
            ],
            "operator_instruction": instruction,
        }

    def make_double_shifted_definition(
        self,
        name: str,
        shifted_slots: list[int],
        normal_slots: list[int],
        instruction: str,
        note: str,
        severity: int = 2,
    ) -> dict:
        shifted_set = set(shifted_slots)
        if len(shifted_set) != 2:
            raise ValueError("Exactly two shifted slots are required.")
        if shifted_set.intersection(normal_slots):
            raise ValueError("Shifted slots cannot overlap with normal slots.")

        normal_assignments = {slot: "1" for slot in normal_slots}
        blocked_assignments = {slot: "1" for slot in normal_slots}
        state_assignments = {slot: "1" for slot in normal_slots}
        for slot in shifted_slots:
            blocked_assignments[slot] = "1"
            state_assignments[slot] = "3"

        return {
            "name": name,
            "normal_occupancy": self.mask_from_assignments(normal_assignments),
            "blocked_slots": self.mask_from_assignments(blocked_assignments),
            "slot_states": self.mask_from_assignments(state_assignments),
            "anomalies": [
                {
                    "type": "shifted_in_slot_plate",
                    "slots": list(shifted_slots),
                    "severity": severity,
                    "note": note,
                }
            ],
            "operator_instruction": instruction,
        }

    def add_definition(self, definition: dict) -> None:
        config_id = f"cfg_{len(self.configs) + 1:06d}"
        self.configs.append(
            {
                "id": config_id,
                "name": definition["name"],
                "normal_occupancy": definition["normal_occupancy"],
                "blocked_slots": definition["blocked_slots"],
                "slot_states": definition["slot_states"],
                "anomalies": definition["anomalies"],
                "operator_instruction": definition["operator_instruction"],
            }
        )

    def add_summary(self, scenario_name: str, count: int) -> None:
        self.scenario_summary.append((scenario_name, count))

    def adjacent_group_slots(self, min_length: int, max_length: int, allowed_slots: list[int] | None = None) -> list[int]:
        allowed = allowed_slots or self.all_slots
        max_length = min(max_length, len(allowed))
        min_length = min(min_length, max_length)
        length = self.rng.randint(min_length, max_length)
        allowed_set = set(allowed)
        min_slot = min(allowed)
        max_slot = max(allowed)

        possible_starts = []
        for start in range(min_slot, max_slot - length + 2):
            candidate = list(range(start, start + length))
            if all(slot in allowed_set for slot in candidate):
                possible_starts.append(start)

        if not possible_starts:
            return sorted(allowed[:length])

        start = self.rng.choice(possible_starts)
        return list(range(start, start + length))

    def separated_groups_slots(self, group_count: int) -> list[int]:
        for _ in range(200):
            selected: set[int] = set()
            ok = True
            for _ in range(group_count):
                placed = False
                for _ in range(100):
                    length = self.rng.randint(2, min(5, self.slot_count))
                    start = self.rng.randint(1, self.slot_count - length + 1)
                    candidate = set(range(start, start + length))
                    if any(
                        slot in selected or (slot - 1) in selected or (slot + 1) in selected
                        for slot in candidate
                    ):
                        continue
                    selected.update(candidate)
                    placed = True
                    break
                if not placed:
                    ok = False
                    break
            if ok:
                return sorted(selected)

        return self.adjacent_group_slots(2, min(6, self.slot_count))

    def set_total_slot_count(self, base_slots: list[int], target_count: int, candidates: list[int] | None = None) -> list[int]:
        allowed = candidates or self.all_slots
        selected = set(base_slots)

        while len(selected) < target_count:
            missing = [slot for slot in allowed if slot not in selected]
            selected.add(self.rng.choice(missing))

        while len(selected) > target_count:
            selected.remove(self.rng.choice(sorted(selected)))

        return sorted(selected)

    def realistic_slots(self) -> list[int]:
        target_count = self.rng.randint(min(8, max(1, self.slot_count - 1)), min(22, max(1, self.slot_count - 1)))
        template = self.rng.randint(1, 3)

        if template == 1:
            groups = self.separated_groups_slots(self.rng.randint(2, 3))
            return self.set_total_slot_count(groups, target_count)

        if template == 2:
            empty_count = max(1, self.slot_count - target_count)
            empty_slots = set(self.random_distinct_slots(empty_count, self.all_slots))
            return [slot for slot in self.all_slots if slot not in empty_slots]

        edge_bias = list(range(1, min(10, self.slot_count) + 1))
        if self.rng.randint(0, 1) == 1:
            edge_bias = list(range(max(1, self.slot_count - 9), self.slot_count + 1))
        base = self.adjacent_group_slots(4, min(10, len(edge_bias)), edge_bias)
        return self.set_total_slot_count(base, target_count)

    def shifted_normal_slots(self, shifted_slot: int, total_blocked_count: int, preferred_candidates: list[int] | None = None) -> list[int]:
        normal_count = max(0, total_blocked_count - 1)
        if normal_count == 0:
            return []

        preferred = [slot for slot in (preferred_candidates or self.all_slots) if slot != shifted_slot]
        fallback = [slot for slot in self.all_slots if slot != shifted_slot and slot not in preferred]

        if len(preferred) >= normal_count:
            return self.random_distinct_slots(normal_count, preferred)

        taken = preferred[:]
        remaining = normal_count - len(taken)
        taken.extend(self.random_distinct_slots(remaining, fallback))
        return sorted(taken)

    def shifted_normal_slots_multi(
        self,
        shifted_slots: list[int],
        total_blocked_count: int,
        preferred_candidates: list[int] | None = None,
    ) -> list[int]:
        shifted_set = set(shifted_slots)
        normal_count = max(0, total_blocked_count - len(shifted_set))
        if normal_count == 0:
            return []

        preferred_base = preferred_candidates or self.all_slots
        preferred = [slot for slot in preferred_base if slot not in shifted_set]
        fallback = [slot for slot in self.all_slots if slot not in shifted_set and slot not in preferred]

        if len(preferred) >= normal_count:
            return self.random_distinct_slots(normal_count, preferred)

        taken = preferred[:]
        remaining = normal_count - len(taken)
        taken.extend(self.random_distinct_slots(remaining, fallback))
        return sorted(taken)

    def generate(self) -> dict:
        for index in range(1, NORMAL_SCENARIO_COUNTS["empty_cassette"] + 1):
            self.add_definition(
                self.make_normal_definition(
                    f"empty_cassette_{index:04d}",
                    [],
                    "Оставить кассету пустой.",
                )
            )
        self.add_summary("empty_cassette", NORMAL_SCENARIO_COUNTS["empty_cassette"])

        for index in range(1, NORMAL_SCENARIO_COUNTS["full_cassette"] + 1):
            self.add_definition(
                self.make_normal_definition(
                    f"full_cassette_{index:04d}",
                    self.all_slots,
                    "Заполнить все слоты.",
                )
            )
        self.add_summary("full_cassette", NORMAL_SCENARIO_COUNTS["full_cassette"])

        for index in range(1, NORMAL_SCENARIO_COUNTS["single_plate"] + 1):
            slot = self.rng.randint(1, self.slot_count)
            self.add_definition(
                self.make_normal_definition(
                    f"single_plate_{index:04d}",
                    [slot],
                    f"Установить одну пластину в слот {slot}.",
                )
            )
        self.add_summary("single_plate", NORMAL_SCENARIO_COUNTS["single_plate"])

        for index in range(1, NORMAL_SCENARIO_COUNTS["full_minus_one"] + 1):
            empty_slot = ((index - 1) % self.slot_count) + 1
            normal_slots = [slot for slot in self.all_slots if slot != empty_slot]
            self.add_definition(
                self.make_normal_definition(
                    f"full_minus_one_{index:04d}",
                    normal_slots,
                    f"Заполнить кассету полностью, оставив пустым слот {empty_slot}.",
                )
            )
        self.add_summary("full_minus_one", NORMAL_SCENARIO_COUNTS["full_minus_one"])

        for index in range(1, NORMAL_SCENARIO_COUNTS["sparse_fill"] + 1):
            count = self.range_count(2, 5)
            slots = self.random_distinct_slots(count, self.all_slots)
            self.add_definition(
                self.make_normal_definition(
                    f"sparse_fill_{index:04d}",
                    slots,
                    f"Редкое заполнение: установить пластины в слоты {self.format_slot_list(slots)}.",
                )
            )
        self.add_summary("sparse_fill", NORMAL_SCENARIO_COUNTS["sparse_fill"])

        for index in range(1, NORMAL_SCENARIO_COUNTS["medium_fill"] + 1):
            count = self.range_count(6, 15)
            slots = self.random_distinct_slots(count, self.all_slots)
            self.add_definition(
                self.make_normal_definition(
                    f"medium_fill_{index:04d}",
                    slots,
                    f"Среднее заполнение: установить пластины в слоты {self.format_slot_list(slots)}.",
                )
            )
        self.add_summary("medium_fill", NORMAL_SCENARIO_COUNTS["medium_fill"])

        for index in range(1, NORMAL_SCENARIO_COUNTS["dense_fill"] + 1):
            count = self.range_count(16, 22)
            slots = self.random_distinct_slots(count, self.all_slots)
            self.add_definition(
                self.make_normal_definition(
                    f"dense_fill_{index:04d}",
                    slots,
                    f"Плотное заполнение: установить пластины в слоты {self.format_slot_list(slots)}.",
                )
            )
        self.add_summary("dense_fill", NORMAL_SCENARIO_COUNTS["dense_fill"])

        for index in range(1, NORMAL_SCENARIO_COUNTS["adjacent_group"] + 1):
            slots = self.adjacent_group_slots(2, min(8, self.slot_count))
            self.add_definition(
                self.make_normal_definition(
                    f"adjacent_group_{index:04d}",
                    slots,
                    f"Сформировать одну группу соседних пластин в слотах {self.format_slot_list(slots)}.",
                )
            )
        self.add_summary("adjacent_group", NORMAL_SCENARIO_COUNTS["adjacent_group"])

        for index in range(1, NORMAL_SCENARIO_COUNTS["separated_groups"] + 1):
            slots = self.separated_groups_slots(self.rng.randint(2, 3))
            self.add_definition(
                self.make_normal_definition(
                    f"separated_groups_{index:04d}",
                    slots,
                    f"Сформировать несколько разнесенных групп в слотах {self.format_slot_list(slots)}.",
                )
            )
        self.add_summary("separated_groups", NORMAL_SCENARIO_COUNTS["separated_groups"])

        for index in range(1, NORMAL_SCENARIO_COUNTS["zone_fill"] + 1):
            zone_variant = (index - 1) % 3
            if zone_variant == 0:
                zone_name = "upper"
                zone_label = "верх"
            elif zone_variant == 1:
                zone_name = "middle"
                zone_label = "середина"
            else:
                zone_name = "lower"
                zone_label = "низ"
            slots = self.zone_slots(zone_name)
            self.add_definition(
                self.make_normal_definition(
                    f"zone_fill_{zone_name}_{index:04d}",
                    slots,
                    f"Заполнить {zone_label} кассеты.",
                )
            )
        self.add_summary("zone_fill", NORMAL_SCENARIO_COUNTS["zone_fill"])

        for index in range(1, NORMAL_SCENARIO_COUNTS["alternating"] + 1):
            phase = 0 if index % 2 == 0 else 1
            slots = [slot for slot in self.all_slots if (slot + phase) % 2 == 1]
            phase_label = "чередование с первого слота" if phase == 1 else "чередование со второго слота"
            self.add_definition(
                self.make_normal_definition(
                    f"alternating_{index:04d}",
                    slots,
                    f"Заполнить кассету по схеме '{phase_label}': слоты {self.format_slot_list(slots)}.",
                )
            )
        self.add_summary("alternating", NORMAL_SCENARIO_COUNTS["alternating"])

        for index in range(1, NORMAL_SCENARIO_COUNTS["production_mix"] + 1):
            slots = self.realistic_slots()
            self.add_definition(
                self.make_normal_definition(
                    f"production_mix_{index:04d}",
                    slots,
                    f"Реалистичная производственная комбинация: установить пластины в слоты {self.format_slot_list(slots)}.",
                )
            )
        self.add_summary("production_mix", NORMAL_SCENARIO_COUNTS["production_mix"])

        for index in range(1, SHIFTED_SCENARIO_COUNTS["shifted_single"] + 1):
            shifted_slot = ((index - 1) % self.slot_count) + 1
            self.add_definition(
                self.make_shifted_definition(
                    f"shifted_single_{index:04d}",
                    shifted_slot,
                    [],
                    f"Установить одну пластину с явным перекосом в слот {shifted_slot}.",
                    "Одна пластина стоит в своем слоте, но заметно перекошена.",
                )
            )
        self.add_summary("shifted_single", SHIFTED_SCENARIO_COUNTS["shifted_single"])

        for index in range(1, SHIFTED_SCENARIO_COUNTS["shifted_full_minus_one"] + 1):
            shifted_slot = ((index - 1) % self.slot_count) + 1
            empty_slot = (index % self.slot_count) + 1
            if empty_slot == shifted_slot:
                empty_slot = ((index + 1) % self.slot_count) + 1
            normal_slots = [slot for slot in self.all_slots if slot not in {shifted_slot, empty_slot}]
            self.add_definition(
                self.make_shifted_definition(
                    f"shifted_full_minus_one_{index:04d}",
                    shifted_slot,
                    normal_slots,
                    f"Почти полная кассета: оставить слот {empty_slot} пустым, а слот {shifted_slot} занять пластиной с явным перекосом.",
                    "Почти полная кассета с одним перекошенным слотом.",
                )
            )
        self.add_summary("shifted_full_minus_one", SHIFTED_SCENARIO_COUNTS["shifted_full_minus_one"])

        for index in range(1, SHIFTED_SCENARIO_COUNTS["shifted_sparse"] + 1):
            shifted_slot = self.rng.randint(1, self.slot_count)
            total_count = self.range_count(2, 5)
            normal_slots = self.shifted_normal_slots(shifted_slot, total_count)
            self.add_definition(
                self.make_shifted_definition(
                    f"shifted_sparse_{index:04d}",
                    shifted_slot,
                    normal_slots,
                    f"Редкое заполнение с перекосом: перекошенная пластина в слоте {shifted_slot}, остальные пластины в слотах {self.format_slot_list(normal_slots)}.",
                    "Перекошенная пластина на фоне редкого заполнения.",
                )
            )
        self.add_summary("shifted_sparse", SHIFTED_SCENARIO_COUNTS["shifted_sparse"])

        for index in range(1, SHIFTED_SCENARIO_COUNTS["shifted_medium"] + 1):
            shifted_slot = self.rng.randint(1, self.slot_count)
            total_count = self.range_count(6, 15)
            normal_slots = self.shifted_normal_slots(shifted_slot, total_count)
            self.add_definition(
                self.make_shifted_definition(
                    f"shifted_medium_{index:04d}",
                    shifted_slot,
                    normal_slots,
                    f"Среднее заполнение с перекосом: перекошенная пластина в слоте {shifted_slot}, остальные пластины в слотах {self.format_slot_list(normal_slots)}.",
                    "Перекошенная пластина на фоне среднего заполнения.",
                )
            )
        self.add_summary("shifted_medium", SHIFTED_SCENARIO_COUNTS["shifted_medium"])

        for index in range(1, SHIFTED_SCENARIO_COUNTS["shifted_dense"] + 1):
            shifted_slot = self.rng.randint(1, self.slot_count)
            total_count = self.range_count(16, 22)
            normal_slots = self.shifted_normal_slots(shifted_slot, total_count)
            self.add_definition(
                self.make_shifted_definition(
                    f"shifted_dense_{index:04d}",
                    shifted_slot,
                    normal_slots,
                    f"Плотное заполнение с перекосом: перекошенная пластина в слоте {shifted_slot}, остальные пластины в слотах {self.format_slot_list(normal_slots)}.",
                    "Перекошенная пластина на фоне плотного заполнения.",
                )
            )
        self.add_summary("shifted_dense", SHIFTED_SCENARIO_COUNTS["shifted_dense"])

        for index in range(1, SHIFTED_SCENARIO_COUNTS["shifted_adjacent_group"] + 1):
            group_slots = self.adjacent_group_slots(3, min(8, self.slot_count))
            shifted_slot = self.rng.choice(group_slots)
            normal_slots = [slot for slot in group_slots if slot != shifted_slot]
            self.add_definition(
                self.make_shifted_definition(
                    f"shifted_adjacent_group_{index:04d}",
                    shifted_slot,
                    normal_slots,
                    f"Сформировать группу соседних пластин, при этом в слоте {shifted_slot} пластина должна стоять с перекосом. Остальные пластины: {self.format_slot_list(normal_slots)}.",
                    "Перекошенная пластина внутри группы соседних пластин.",
                )
            )
        self.add_summary("shifted_adjacent_group", SHIFTED_SCENARIO_COUNTS["shifted_adjacent_group"])

        for index in range(1, SHIFTED_SCENARIO_COUNTS["shifted_separated_groups"] + 1):
            slots = self.separated_groups_slots(self.rng.randint(2, 3))
            shifted_slot = self.rng.choice(slots)
            normal_slots = [slot for slot in slots if slot != shifted_slot]
            self.add_definition(
                self.make_shifted_definition(
                    f"shifted_separated_groups_{index:04d}",
                    shifted_slot,
                    normal_slots,
                    f"Сформировать несколько разнесённых групп. В слоте {shifted_slot} пластина должна стоять с перекосом, остальные пластины: {self.format_slot_list(normal_slots)}.",
                    "Несколько разнесённых групп с одним перекошенным слотом.",
                )
            )
        self.add_summary("shifted_separated_groups", SHIFTED_SCENARIO_COUNTS["shifted_separated_groups"])

        for index in range(1, SHIFTED_SCENARIO_COUNTS["shifted_double"] + 1):
            shifted_slots = self.random_distinct_slots(2, self.all_slots)
            total_count = self.rng.randint(2, min(6, self.slot_count))
            normal_slots = self.shifted_normal_slots_multi(shifted_slots, total_count)
            self.add_definition(
                self.make_double_shifted_definition(
                    f"shifted_double_{index:04d}",
                    shifted_slots,
                    normal_slots,
                    f"Установить две пластины с явным перекосом в слоты {self.format_slot_list(shifted_slots)}. Остальные пластины: {self.format_slot_list(normal_slots)}.",
                    "Два перекошенных слота в одной кассете.",
                )
            )
        self.add_summary("shifted_double", SHIFTED_SCENARIO_COUNTS["shifted_double"])

        return {
            "project": self.project,
            "cassette_size_mm": self.cassette_size_mm,
            "slot_count": self.slot_count,
            "shots_per_config": self.shots_per_config,
            "default_exposure_us": self.default_exposure_us,
            "default_gain": self.default_gain,
            "configs": self.configs,
        }


def main() -> None:
    args = parse_args()
    generator = PlanGenerator(
        project=args.project,
        cassette_size_mm=args.cassette_size_mm,
        slot_count=args.slot_count,
        shots_per_config=args.shots_per_config,
        default_exposure_us=args.default_exposure_us,
        default_gain=args.default_gain,
        seed=args.seed,
    )

    plan = generator.generate()
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    normal_total = sum(NORMAL_SCENARIO_COUNTS.values())
    shifted_total = sum(SHIFTED_SCENARIO_COUNTS.values())
    grand_total = normal_total + shifted_total

    print(f"Saved {len(generator.configs)} configurations to {output_path.resolve()}")
    print(f"Normal scenarios:  {normal_total}")
    print(f"Shifted scenarios: {shifted_total}")
    print(f"Grand total:       {grand_total}")
    print()
    print("Scenario breakdown:")
    for scenario_name, count in generator.scenario_summary:
        print(f"- {scenario_name}: {count}")


if __name__ == "__main__":
    main()
