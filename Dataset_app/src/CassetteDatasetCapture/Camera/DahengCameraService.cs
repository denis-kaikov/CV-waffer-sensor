#if HAS_GALAXY_SDK
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using GxIAPINET;

namespace CassetteDatasetCapture.Camera;

public sealed class DahengCameraService : ICameraService
{
    private IGXDevice? _device;
    private IGXStream? _stream;
    private IGXFeatureControl? _remote;
    private IGXImageFormatConvert? _converter;
    private bool _sdkInitialized;

    public bool IsConnected { get; private set; }
    public bool IsLive { get; private set; }
    public double ExposureUs { get; set; } = 8000;
    public double Gain { get; set; } = 0;
    public string? SerialNumber { get; set; }
    public int FrameTimeoutMs { get; set; } = 2000;

    public void Connect()
    {
        if (IsConnected) return;
        try
        {
            var factory = IGXFactory.GetInstance();
            factory.Init();
            _sdkInitialized = true;

            var devices = new List<IGXDeviceInfo>();
            factory.UpdateAllDeviceList(300, devices);
            if (devices.Count == 0)
            {
                throw new CameraException("No Daheng camera found. Check power, Ethernet connection, IP configuration, and firewall.");
            }

            var deviceInfo = SelectDevice(devices);
            _device = string.IsNullOrWhiteSpace(SerialNumber)
                ? factory.OpenDeviceBySN(deviceInfo.GetSN(), GX_ACCESS_MODE.GX_ACCESS_EXCLUSIVE)
                : factory.OpenDeviceBySN(SerialNumber, GX_ACCESS_MODE.GX_ACCESS_EXCLUSIVE);

            _remote = _device.GetRemoteFeatureControl();
            _stream = _device.OpenStream(0);
            _converter = factory.CreateImageFormatConvert();

            ApplyBasicSettings();
            IsConnected = true;
        }
        catch (CameraException)
        {
            Disconnect();
            throw;
        }
        catch (DllNotFoundException ex)
        {
            Disconnect();
            throw new CameraException("GxIAPINET.dll not found or dependent Galaxy SDK binaries are missing.", ex);
        }
        catch (Exception ex)
        {
            Disconnect();
            throw new CameraException("Failed to connect to Daheng camera.", ex);
        }
    }

    public void Disconnect()
    {
        try { StopLive(); } catch { }
        _stream = null;
        _remote = null;
        _device?.Close();
        _device = null;
        if (_sdkInitialized)
        {
            IGXFactory.GetInstance().Uninit();
            _sdkInitialized = false;
        }
        IsConnected = false;
    }

    public void StartLive()
    {
        if (!IsConnected) Connect();
        if (IsLive) return;
        _stream!.StartGrab();
        _remote!.GetCommandFeature("AcquisitionStart").Execute();
        IsLive = true;
    }

    public void StopLive()
    {
        if (!IsLive) return;
        try { _remote?.GetCommandFeature("AcquisitionStop").Execute(); } catch { }
        try { _stream?.StopGrab(); } catch { }
        IsLive = false;
    }

    public Bitmap GrabFrame()
    {
        if (!IsConnected) Connect();
        if (!IsLive) StartLive();
        if (_stream is null || _converter is null) throw new CameraException("Camera stream is not initialized.");

        IFrameData? frameData = null;
        try
        {
            frameData = _stream.DQBuf((uint)FrameTimeoutMs);
            if (frameData.GetStatus() != GX_FRAME_STATUS_LIST.GX_FRAME_STATUS_SUCCESS)
            {
                throw new CameraException("Frame timeout or acquisition failed.");
            }

            return ConvertFrame(frameData);
        }
        catch (CGalaxyException ex)
        {
            throw new CameraException("Acquisition failed on the Daheng camera.", ex);
        }
        catch (Exception ex) when (ex is not CameraException)
        {
            throw new CameraException("Failed to grab frame from Daheng camera.", ex);
        }
        finally
        {
            if (frameData is not null)
            {
                try { _stream.QBuf(frameData); } catch { }
            }
        }
    }

    public void Dispose() => Disconnect();

    private void ApplyBasicSettings()
    {
        if (_remote is null) return;
        TrySetEnum("ExposureAuto", "Off");
        TrySetEnum("GainAuto", "Off");
        TrySetFloat("ExposureTime", ExposureUs);
        TrySetFloat("Gain", Gain);
        TrySetEnum("TriggerMode", "Off");
        TrySetEnum("PixelFormat", "Mono8");
    }

    private void TrySetEnum(string name, string value)
    {
        if (_remote?.IsImplemented(name) == true && _remote.IsWritable(name))
        {
            _remote.GetEnumFeature(name).SetValue(value);
        }
    }

    private void TrySetFloat(string name, double value)
    {
        if (_remote?.IsImplemented(name) == true && _remote.IsWritable(name))
        {
            _remote.GetFloatFeature(name).SetValue(value);
        }
    }

    private IGXDeviceInfo SelectDevice(List<IGXDeviceInfo> devices)
    {
        if (string.IsNullOrWhiteSpace(SerialNumber))
            return devices[0];

        return devices.FirstOrDefault(d => string.Equals(d.GetSN(), SerialNumber, StringComparison.OrdinalIgnoreCase))
            ?? throw new CameraException($"No Daheng camera with serial number '{SerialNumber}' was found.");
    }

    private Bitmap ConvertFrame(IBaseData frameData)
    {
        var pixelFormat = frameData.GetPixelFormat();
        var width = (int)frameData.GetWidth();
        var height = (int)frameData.GetHeight();

        if (pixelFormat == GX_PIXEL_FORMAT_ENTRY.GX_PIXEL_FORMAT_BGR8)
        {
            return CreateBitmapFromBgr(frameData.GetBuffer(), width, height);
        }

        _converter!.SetDstFormat(GX_PIXEL_FORMAT_ENTRY.GX_PIXEL_FORMAT_MONO8);
        var dstSize = _converter.GetBufferSizeForConversion(frameData);
        using var buffer = new PinnedBuffer((int)dstSize);
        _converter.Convert(frameData, buffer.Pointer, dstSize, true);
        return CreateBitmapFromMono(buffer.Data, width, height);
    }

    private static Bitmap CreateBitmapFromMono(byte[] data, int width, int height)
    {
        var bitmap = new Bitmap(width, height, PixelFormat.Format8bppIndexed);
        var palette = bitmap.Palette;
        for (var i = 0; i < 256; i++) palette.Entries[i] = Color.FromArgb(i, i, i);
        bitmap.Palette = palette;

        var rect = new Rectangle(0, 0, width, height);
        var bd = bitmap.LockBits(rect, ImageLockMode.WriteOnly, PixelFormat.Format8bppIndexed);
        try
        {
            var sourceStride = width;
            var targetStride = Math.Abs(bd.Stride);
            var row = new byte[sourceStride];
            for (var y = 0; y < height; y++)
            {
                var sourceOffset = y * sourceStride;
                if (sourceOffset + sourceStride > data.Length) break;
                Buffer.BlockCopy(data, sourceOffset, row, 0, sourceStride);
                Marshal.Copy(row, 0, IntPtr.Add(bd.Scan0, y * bd.Stride), Math.Min(sourceStride, targetStride));
            }
        }
        finally
        {
            bitmap.UnlockBits(bd);
        }
        return bitmap;
    }

    private static Bitmap CreateBitmapFromBgr(IntPtr buffer, int width, int height)
    {
        var bitmap = new Bitmap(width, height, PixelFormat.Format24bppRgb);
        var rect = new Rectangle(0, 0, width, height);
        var bd = bitmap.LockBits(rect, ImageLockMode.WriteOnly, PixelFormat.Format24bppRgb);
        try
        {
            var sourceStride = width * 3;
            var targetStride = Math.Abs(bd.Stride);
            var row = new byte[sourceStride];
            for (var y = 0; y < height; y++)
            {
                Marshal.Copy(IntPtr.Add(buffer, y * sourceStride), row, 0, sourceStride);
                Marshal.Copy(row, 0, IntPtr.Add(bd.Scan0, y * bd.Stride), Math.Min(sourceStride, targetStride));
            }
        }
        finally
        {
            bitmap.UnlockBits(bd);
        }
        return bitmap;
    }

    private sealed class PinnedBuffer : IDisposable
    {
        private readonly GCHandle _handle;
        public byte[] Data { get; }
        public IntPtr Pointer => _handle.AddrOfPinnedObject();
        public PinnedBuffer(int size)
        {
            Data = new byte[size];
            _handle = GCHandle.Alloc(Data, GCHandleType.Pinned);
        }
        public void Dispose()
        {
            if (_handle.IsAllocated) _handle.Free();
        }
    }
}
#endif
