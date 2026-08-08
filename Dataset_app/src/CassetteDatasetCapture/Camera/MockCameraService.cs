using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;

namespace CassetteDatasetCapture.Camera;

public sealed class MockCameraService : ICameraService
{
    private readonly Random _random = new(1234);
    public bool IsConnected { get; private set; }
    public bool IsLive { get; private set; }
    public double ExposureUs { get; set; } = 8000;
    public double Gain { get; set; } = 0;

    public void Connect() => IsConnected = true;
    public void Disconnect() => IsConnected = false;
    public void StartLive() => IsLive = true;
    public void StopLive() => IsLive = false;

    public Bitmap GrabFrame()
    {
        var bmp = new Bitmap(960, 540, PixelFormat.Format24bppRgb);
        using var g = Graphics.FromImage(bmp);
        g.SmoothingMode = SmoothingMode.AntiAlias;
        g.Clear(Color.FromArgb(32, 36, 48));
        using var br = new LinearGradientBrush(new Rectangle(0, 0, bmp.Width, bmp.Height), Color.FromArgb(58, 68, 88), Color.FromArgb(18, 20, 28), 90);
        g.FillRectangle(br, 0, 0, bmp.Width, bmp.Height);
        for (var i = 0; i < 12; i++) g.DrawEllipse(Pens.DimGray, _random.Next(20, 900), _random.Next(20, 500), _random.Next(30, 120), _random.Next(30, 120));
        g.DrawString($"Mock frame {DateTime.Now:HH:mm:ss}", SystemFonts.DefaultFont, Brushes.White, 24, 24);
        return bmp;
    }

    public void Dispose() { }
}
