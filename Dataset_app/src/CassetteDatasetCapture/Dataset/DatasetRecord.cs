using CassetteDatasetCapture.Model;

namespace CassetteDatasetCapture.Dataset;

public sealed class DatasetRecord
{
    public required string ImagePath { get; set; }
    public required int CassetteSizeMm { get; set; }
    public required int SlotCount { get; set; }
    public required string ConfigId { get; set; }
    public required int ShotIndex { get; set; }
    public required string NormalOccupancy { get; set; }
    public required string BlockedSlots { get; set; }
    public required string SlotStates { get; set; }
    public required IReadOnlyList<CassetteAnomaly> Anomalies { get; set; }
    public required string ImageQuality { get; set; }
    public required double ExposureUs { get; set; }
    public required double Gain { get; set; }
    public required DateTimeOffset Timestamp { get; set; }
    public required string OperatorName { get; set; }
    public required string Status { get; set; }
    public required string Notes { get; set; }
}
