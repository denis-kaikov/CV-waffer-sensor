using System.Drawing;

namespace CassetteDatasetCapture.Camera;

public interface ICameraService : IDisposable
{
    bool IsConnected { get; }
    bool IsLive { get; }
    double ExposureUs { get; set; }
    double Gain { get; set; }
    void Connect();
    void Disconnect();
    void StartLive();
    void StopLive();
    Bitmap GrabFrame();
}
