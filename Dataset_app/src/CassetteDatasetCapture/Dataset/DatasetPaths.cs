namespace CassetteDatasetCapture.Dataset;

public sealed class DatasetPaths
{
    public required string Root { get; init; }
    public string ImagesRoot => Path.Combine(Root, "images");
    public string RejectedRoot => Path.Combine(Root, "rejected");
    public string LabelsCsv => Path.Combine(Root, "labels.csv");
    public string LabelsJsonl => Path.Combine(Root, "labels.jsonl");
    public string ProgressJson => Path.Combine(Root, "progress.json");
}
