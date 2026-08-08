using CassetteDatasetCapture.Dataset;
using CassetteDatasetCapture.Model;

namespace CassetteDatasetCapture.Tests;

public class DatasetWriterTests
{
    [Fact]
    public void AppendWritesCsvAndJsonl()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        var writer = new DatasetWriter(new DatasetPaths { Root = root });
        writer.Append(new DatasetRecord
        {
            ImagePath = "images/a.png",
            CassetteSizeMm = 150,
            SlotCount = 1,
            ConfigId = "cfg_1",
            ShotIndex = 1,
            NormalOccupancy = "1",
            BlockedSlots = "1",
            SlotStates = "1",
            Anomalies = [],
            ImageQuality = "ok",
            ExposureUs = 8000,
            Gain = 0,
            Timestamp = DateTimeOffset.UtcNow,
            OperatorName = "op",
            Status = "accepted",
            Notes = string.Empty
        });

        Assert.True(File.Exists(Path.Combine(root, "labels.csv")));
        Assert.True(File.Exists(Path.Combine(root, "labels.jsonl")));
    }
}
