namespace CassetteDatasetCapture.Dataset;

public sealed class ProgressState
{
    public string Project { get; set; } = string.Empty;
    public string CurrentConfigId { get; set; } = string.Empty;
    public Dictionary<string, ProgressItem> Configs { get; set; } = new();
}
