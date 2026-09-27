#if !HAS_GALAXY_SDK
using System.Drawing;

namespace CassetteDatasetCapture.Camera;

public sealed class DahengCameraService : ICameraService
{
    public bool IsConnected { get; private set; }
    public bool IsLive { get; private set; }
    public double ExposureUs { get; private set; } = 8000;
    public double Gain { get; private set; } = 0;
    public string? SerialNumber { get; set; }
    public int FrameTimeoutMs { get; set; } = 500;

    public void ApplySettings(CameraSettings settings)
    {
        ExposureUs = settings.ExposureUs;
        Gain = settings.Gain;
    }

    public void Connect()
    {
        throw new CameraException("Galaxy SDK is not configured for this build. Use the test camera or add GxIAPINET.dll to src/CassetteDatasetCapture/Dependencies.");
    }

    public void Disconnect()
    {
        IsConnected = false;
        IsLive = false;
    }

    public void StartLive()
    {
        throw new CameraException("Galaxy SDK is not configured for this build. Use the test camera or add GxIAPINET.dll to src/CassetteDatasetCapture/Dependencies.");
    }

    public void StopLive()
    {
        IsLive = false;
    }

    public Bitmap GrabFrame()
    {
        throw new CameraException("Galaxy SDK is not configured for this build. Use the test camera or add GxIAPINET.dll to src/CassetteDatasetCapture/Dependencies.");
    }

    public void Dispose() => Disconnect();
}
#endif
