using System.Drawing;

namespace CassetteDatasetCapture.Camera;

public interface ICameraService : IDisposable
{
    bool IsConnected { get; }
    bool IsLive { get; }
    double ExposureUs { get; }
    double Gain { get; }
    void ApplySettings(CameraSettings settings);
    void Connect();
    void Disconnect();
    void StartLive();
    void StopLive();
    Bitmap GrabFrame();
}
