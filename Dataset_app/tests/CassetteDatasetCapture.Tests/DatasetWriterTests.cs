using CassetteDatasetCapture.Camera;
using CassetteDatasetCapture.Dataset;
using CassetteDatasetCapture.Model;

namespace CassetteDatasetCapture.Tests;

public class DatasetWriterTests
{
    [Fact]
    public void CameraSettingsChangeLiveFrameBrightness()
    {
        using var darkCamera = new MockCameraService();
        darkCamera.ApplySettings(new CameraSettings { ExposureUs = 1000, Gain = 0 });
        darkCamera.StartLive();
        using var darkFrame = darkCamera.GrabFrame();

        using var brightCamera = new MockCameraService();
        brightCamera.ApplySettings(new CameraSettings { ExposureUs = 16000, Gain = 6 });
        using var brightFrame = brightCamera.GrabFrame();

        Assert.Equal(1000, darkCamera.ExposureUs);
        Assert.Equal(6, brightCamera.Gain);
        Assert.True(darkCamera.IsConnected);
        Assert.True(darkCamera.IsLive);
        Assert.True(brightFrame.GetPixel(700, 400).GetBrightness() > darkFrame.GetPixel(700, 400).GetBrightness());
    }

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
