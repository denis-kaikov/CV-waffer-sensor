using System.Text.Json.Serialization;

namespace CassetteDatasetCapture.CapturePlan;

public sealed class CapturePlan
{
    [JsonPropertyName("project")]
    public string Project { get; set; } = string.Empty;

    [JsonPropertyName("cassette_size_mm")]
    public int CassetteSizeMm { get; set; }

    [JsonPropertyName("slot_count")]
    public int SlotCount { get; set; }

    [JsonPropertyName("shots_per_config")]
    public int ShotsPerConfig { get; set; } = 1;

    [JsonPropertyName("default_exposure_us")]
    public double DefaultExposureUs { get; set; } = 8000;

    [JsonPropertyName("default_gain")]
    public double DefaultGain { get; set; } = 0;

    [JsonPropertyName("configs")]
    public List<CaptureConfig> Configs { get; set; } = new();
}
