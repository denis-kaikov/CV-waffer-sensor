namespace CassetteDatasetCapture.Utils;

public static class ImageFileNameUtil
{
    public static string CreateFileName(string configId, int shotIndex) => $"{configId}_{TimeUtil.TimestampNow()}_{shotIndex:000}.png";
}
