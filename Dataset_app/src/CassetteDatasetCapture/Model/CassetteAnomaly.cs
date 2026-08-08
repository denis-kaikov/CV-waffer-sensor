using System.Text.Json.Serialization;

namespace CassetteDatasetCapture.Model;

public sealed class CassetteAnomaly
{
    [JsonPropertyName("type")]
    public string Type { get; set; } = string.Empty;
    [JsonPropertyName("slots")]
    public int[] Slots { get; set; } = Array.Empty<int>();
    [JsonPropertyName("severity")]
    public int Severity { get; set; } = 1;
    [JsonPropertyName("note")]
    public string Note { get; set; } = string.Empty;
}
