namespace CassetteDatasetCapture.Dataset;

public sealed class ProgressItem
{
    public string Status { get; set; } = "pending";
    public int ShotsDone { get; set; }
}
