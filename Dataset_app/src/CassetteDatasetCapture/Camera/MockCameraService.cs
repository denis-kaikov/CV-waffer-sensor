using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;

namespace CassetteDatasetCapture.Camera;

public sealed class MockCameraService : ICameraService
{
    private readonly Random _random = new(1234);
    public bool IsConnected { get; private set; }
    public bool IsLive { get; private set; }
    public double ExposureUs { get; private set; } = 8000;
    public double Gain { get; private set; } = 0;

    public void ApplySettings(CameraSettings settings)
    {
        ExposureUs = settings.ExposureUs;
        Gain = settings.Gain;
    }

    public void Connect() => IsConnected = true;
    public void Disconnect() => IsConnected = false;
    public void StartLive()
    {
        if (!IsConnected) Connect();
        IsLive = true;
    }
    public void StopLive() => IsLive = false;

    public Bitmap GrabFrame()
    {
        var bmp = new Bitmap(960, 540, PixelFormat.Format24bppRgb);
        using var g = Graphics.FromImage(bmp);
        g.SmoothingMode = SmoothingMode.AntiAlias;
        var brightness = Math.Clamp(ExposureUs / 8000.0 * Math.Pow(10, Gain / 20.0), 0.15, 3.0);
        Color Scale(int red, int green, int blue) => Color.FromArgb(
            Math.Clamp((int)(red * brightness), 0, 255),
            Math.Clamp((int)(green * brightness), 0, 255),
            Math.Clamp((int)(blue * brightness), 0, 255));
        g.Clear(Scale(32, 36, 48));
        using var br = new LinearGradientBrush(new Rectangle(0, 0, bmp.Width, bmp.Height), Scale(58, 68, 88), Scale(18, 20, 28), 90);
        g.FillRectangle(br, 0, 0, bmp.Width, bmp.Height);
        for (var i = 0; i < 12; i++) g.DrawEllipse(Pens.DimGray, _random.Next(20, 900), _random.Next(20, 500), _random.Next(30, 120), _random.Next(30, 120));
        g.DrawString($"Mock frame {DateTime.Now:HH:mm:ss}", SystemFonts.DefaultFont, Brushes.White, 24, 24);
        g.DrawString($"Exposure {ExposureUs:0} us | Gain {Gain:0.0} dB", SystemFonts.DefaultFont, Brushes.White, 24, 48);
        return bmp;
    }

    public void Dispose() { }
}
