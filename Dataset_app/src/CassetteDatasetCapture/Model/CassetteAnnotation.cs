namespace CassetteDatasetCapture.Model;

public sealed class CassetteAnnotation
{
    public int CassetteSizeMm { get; set; }
    public int SlotCount { get; set; }
    public SlotState[] SlotStates { get; set; } = Array.Empty<SlotState>();
    public List<CassetteAnomaly> Anomalies { get; set; } = new();
    public string NormalOccupancy => new(SlotStates.Select(s => s == SlotState.OccupiedOk ? '1' : '0').ToArray());
    public string BlockedSlots => new(SlotStates.Select(s => s == SlotState.Empty ? '0' : '1').ToArray());
    public string SlotStatesString => new(SlotStates.Select(s => ((int)s).ToString()[0]).ToArray());
}
