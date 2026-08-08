namespace CassetteDatasetCapture.CapturePlan;

public static class CapturePlanValidator
{
    public static IReadOnlyList<string> Validate(CapturePlan plan)
    {
        var errors = new List<string>();

        if (plan.SlotCount <= 0)
            errors.Add("slot_count must be greater than zero.");

        if (plan.ShotsPerConfig <= 0)
            errors.Add("shots_per_config must be greater than zero.");

        if (plan.Configs.Count == 0)
            errors.Add("configs must contain at least one item.");

        var duplicatedIds = plan.Configs
            .GroupBy(c => c.Id)
            .Where(g => string.IsNullOrWhiteSpace(g.Key) || g.Count() > 1)
            .Select(g => string.IsNullOrWhiteSpace(g.Key) ? "<empty>" : g.Key);

        foreach (var id in duplicatedIds)
            errors.Add($"config id '{id}' is empty or duplicated.");

        foreach (var cfg in plan.Configs)
        {
            ValidateMask(errors, cfg.Id, "normal_occupancy", cfg.NormalOccupancy, plan.SlotCount, "01");
            ValidateMask(errors, cfg.Id, "blocked_slots", cfg.BlockedSlots, plan.SlotCount, "01");
            ValidateMask(errors, cfg.Id, "slot_states", cfg.SlotStates, plan.SlotCount, "012345");
            ValidateConsistency(errors, cfg, plan.SlotCount);
            ValidateAnomalies(errors, cfg, plan.SlotCount);
        }

        return errors;
    }

    private static void ValidateMask(List<string> errors, string id, string name, string mask, int length, string allowedChars)
    {
        if (mask.Length != length)
            errors.Add($"{id}: {name} length must equal slot_count ({length}).");

        if (mask.Any(c => !allowedChars.Contains(c)))
            errors.Add($"{id}: {name} contains unsupported characters. Allowed: {allowedChars}.");
    }

    private static void ValidateConsistency(List<string> errors, CaptureConfig cfg, int slotCount)
    {
        if (cfg.NormalOccupancy.Length != slotCount || cfg.BlockedSlots.Length != slotCount || cfg.SlotStates.Length != slotCount)
            return;

        for (var i = 0; i < slotCount; i++)
        {
            var slotNumber = i + 1;
            var state = cfg.SlotStates[i];
            var normal = cfg.NormalOccupancy[i];
            var blocked = cfg.BlockedSlots[i];

            if (state == '1' && normal != '1')
                errors.Add($"{cfg.Id}: slot {slotNumber} is OccupiedOk but normal_occupancy is not 1.");

            if (normal == '1' && state != '1')
                errors.Add($"{cfg.Id}: slot {slotNumber} has normal_occupancy=1 but slot_state is not OccupiedOk.");

            if (state != '0' && blocked != '1')
                errors.Add($"{cfg.Id}: slot {slotNumber} has non-empty slot_state but blocked_slots is not 1.");
        }
    }

    private static void ValidateAnomalies(List<string> errors, CaptureConfig cfg, int slotCount)
    {
        foreach (var anomaly in cfg.Anomalies.Where(a => a.Type == "cross_slot_plate"))
        {
            if (anomaly.Slots.Length != 2)
            {
                errors.Add($"{cfg.Id}: cross_slot_plate must contain exactly two slots.");
                continue;
            }

            var first = anomaly.Slots[0];
            var second = anomaly.Slots[1];
            if (first < 1 || second < 1 || first > slotCount || second > slotCount)
                errors.Add($"{cfg.Id}: cross_slot_plate slots must be in range 1..{slotCount}.");

            if (Math.Abs(first - second) != 1)
                errors.Add($"{cfg.Id}: cross_slot_plate slots should be adjacent.");

            if (cfg.SlotStates.Length == slotCount && cfg.BlockedSlots.Length == slotCount && cfg.NormalOccupancy.Length == slotCount)
            {
                foreach (var slot in anomaly.Slots.Where(s => s >= 1 && s <= slotCount))
                {
                    var index = slot - 1;
                    if (cfg.SlotStates[index] != '2')
                        errors.Add($"{cfg.Id}: cross-slot anomaly slot {slot} must have slot_state=2.");
                    if (cfg.BlockedSlots[index] != '1')
                        errors.Add($"{cfg.Id}: cross-slot anomaly slot {slot} must have blocked_slots=1.");
                    if (cfg.NormalOccupancy[index] != '0')
                        errors.Add($"{cfg.Id}: cross-slot anomaly slot {slot} must have normal_occupancy=0.");
                }
            }
        }
    }
}
