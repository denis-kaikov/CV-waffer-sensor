using System.Drawing;

namespace CassetteDatasetCapture.Camera;

public sealed class CameraFrame : IDisposable
{
    public CameraFrame(Bitmap bitmap) => Bitmap = bitmap;
    public Bitmap Bitmap { get; }
    public void Dispose() => Bitmap.Dispose();
}
