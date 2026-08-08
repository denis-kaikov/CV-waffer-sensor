using System.Text.Json.Serialization;
using CassetteDatasetCapture.Model;

namespace CassetteDatasetCapture.CapturePlan;

public sealed class CaptureConfig
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("normal_occupancy")]
    public string NormalOccupancy { get; set; } = string.Empty;

    [JsonPropertyName("blocked_slots")]
    public string BlockedSlots { get; set; } = string.Empty;

    [JsonPropertyName("slot_states")]
    public string SlotStates { get; set; } = string.Empty;

    [JsonPropertyName("anomalies")]
    public List<CassetteAnomaly> Anomalies { get; set; } = new();

    [JsonPropertyName("operator_instruction")]
    public string OperatorInstruction { get; set; } = string.Empty;
}
