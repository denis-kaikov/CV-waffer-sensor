# Galaxy SDK Documentation Notes for CassetteDatasetCapture

## 1. Purpose

This document contains practical Galaxy SDK notes for implementing `DahengCameraService` in the `CassetteDatasetCapture` C#/.NET Windows application.

The first MVP should use `MockCameraService`.  
Real camera integration should be implemented in Phase 2 using Daheng Galaxy Windows SDK.

Target camera:

```text
Daheng MER2-1220-9GM-P
MERCURY2 GigE / PoE
Mono
4024 x 3036
```

---

## 2. Required SDK

Use:

```text
Galaxy Windows SDK
```

Official Daheng software page currently lists Galaxy Windows SDK for:

```text
Windows 7 / 10 / 11
Interfaces:
  CoaXPress
  5GigE
  GigE
  10GigE
  USB3.0
  USB3.2
  USB2.0

Supported products:
  Mercury
  Mercury 2
  Mercury 3
  Mars
  Venus
  Polaris Frame Grabber
```

This project uses a Mercury2 GigE camera, so Galaxy Windows SDK is the correct SDK family.

Do not use the Runtime SDK for development unless only deployment/runtime is needed.  
For development, install the full Galaxy Windows SDK because it includes documentation, headers, libraries, demos, and samples.

---

## 3. Expected installation paths on Windows

After installing Galaxy Windows SDK, check these locations:

```text
C:\Program Files\Daheng Imaging\GalaxySDK\
```

Important subfolders:

```text
C:\Program Files\Daheng Imaging\GalaxySDK\Doc
C:\Program Files\Daheng Imaging\GalaxySDK\Samples
C:\Program Files\Daheng Imaging\GalaxySDK\Demo
C:\Program Files\Daheng Imaging\GalaxySDK\Development
```

Galaxy Viewer executable is typically located around:

```text
C:\Program Files\Daheng Imaging\GalaxySDK\Demo\Win64\GalaxyView.exe
```

GigE IP configuration tool is usually available as:

```text
GxGigEIPConfig.exe
```

The exact path may vary by SDK version. Codex must not hardcode the path unless it is made configurable.

---

## 4. Documentation to look for after SDK installation

Inside the SDK installation, search for:

```text
Doc
Development\Doc
Samples
Development\Samples
```

Look for documents with names similar to:

```text
DotNET SDK Programmer's Guide
DotNET SDK Programming Reference Manual
Galaxy SDK Programmer's Guide
Galaxy SDK User Manual
MERCURY2 GigE Cameras User Manual
```

Also inspect:

```text
C# samples
.NET samples
GxIAPINET samples
```

---

## 5. .NET / C# SDK notes

Daheng/VA Imaging documentation indicates that the SDK includes C#/.NET examples.

The .NET wrapper DLL is expected to be:

```text
GxIAPINET.dll
```

Supported .NET variants reported by VA Imaging:

```text
.NET Framework 3.5 / 4.0:
  use GxIAPINET.dll from the corresponding directory

.NET Core / modern .NET:
  .NET 6.0 and above
  use GxIAPINET.dll from the .NET 6.0 directory
```

Our project target is:

```text
.NET 8
WinForms
```

Therefore Codex should look for the .NET 6.0+ version of `GxIAPINET.dll` and test if it can be referenced from a .NET 8 WinForms project.

If the wrapper only works reliably with .NET 6, downgrade the application target to .NET 6 rather than using P/Invoke immediately.

---

## 6. Source files to inspect before coding DahengCameraService

Codex should inspect installed SDK samples first.

Search in SDK folder for:

```text
*.csproj
*.sln
*.cs
GxIAPINET.dll
GxIAPINET.xml
```

Likely useful sample names may include:

```text
GxSingleCam
SingleCam
Acquisition
GrabImage
GrabCallback
GxMultiCam
```

Do not invent API calls if samples are available.  
The correct implementation should be derived from the installed SDK sample code.

---

## 7. Development approach

### Phase 1 — no real SDK dependency

Keep this working first:

```csharp
ICameraService camera = new MockCameraService();
```

The application must work fully with mock frames:

- load capture plan;
- show slot map;
- capture image;
- save PNG;
- save labels.csv;
- save labels.jsonl;
- save progress.json.

### Phase 2 — Daheng SDK adapter

Implement:

```csharp
DahengCameraService : ICameraService
```

Do not let UI call Galaxy SDK directly.

All Galaxy SDK calls must be hidden behind:

```csharp
ICameraService
```

---

## 8. ICameraService contract

Use this interface:

```csharp
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
```

If the SDK provides asynchronous frame callbacks, they should be wrapped internally.  
The rest of the app should still be able to call:

```csharp
Bitmap frame = camera.GrabFrame();
```

---

## 9. DahengCameraService required behavior

`DahengCameraService` must:

1. Initialize Galaxy SDK / GxIAPINET library.
2. Enumerate available devices.
3. Select the first camera or a camera chosen by serial number.
4. Open the selected camera.
5. Configure acquisition mode.
6. Disable automatic exposure/gain for dataset consistency.
7. Set exposure time.
8. Set gain.
9. Start acquisition.
10. Grab a frame.
11. Convert image buffer to `Bitmap`.
12. Stop acquisition.
13. Close device.
14. Uninitialize SDK on dispose.

---

## 10. Recommended camera parameters for dataset capture

Use fixed parameters for dataset consistency.

Initial values:

```text
ExposureAuto = Off
GainAuto     = Off
ExposureTime = configurable, default 8000 us
Gain         = configurable, default 0
TriggerMode  = Off for MVP
PixelFormat  = Mono8 preferred for MVP
```

If image quality requires more bit depth, add Mono12 support later.

For MVP, convert all frames to 8-bit grayscale Bitmap before saving PNG.

---

## 11. Galaxy Viewer workflow before coding

Before implementing `DahengCameraService`, verify the camera with Galaxy Viewer:

1. Install Galaxy Windows SDK.
2. Connect camera power:
   - either PoE;
   - or external 12–24V via Hirose/I/O cable.
3. Connect Ethernet to laptop/PC.
4. Open Galaxy Viewer.
5. Confirm camera appears in device tree.
6. If not visible, use `GxGigEIPConfig`.
7. Set camera / network adapter to compatible IP subnet.
8. Confirm firewall does not block Galaxy SDK tools.
9. Open camera.
10. Start acquisition.
11. Set:
    - ExposureAuto = Off
    - ExposureTime = desired value
    - GainAuto = Off
    - Gain = desired value
12. Check focus and lighting.
13. Save a test image manually.
14. Record the working parameters.

Only after this works, implement the C# adapter.

---

## 12. GigE camera setup notes

For GigE cameras:

- camera and network adapter must be in compatible IP subnets;
- the camera must be powered;
- firewall can block discovery/streaming;
- jumbo frames may improve throughput;
- use GigE IP Configurator if camera is not discovered;
- avoid Wi-Fi routing involvement;
- prefer direct Ethernet or a dedicated switch;
- use a stable power supply.

Expected topology with external power:

```text
Laptop Ethernet  ->  camera RJ45
12–24V PSU       ->  Hirose/I/O cable -> camera
```

Expected topology with PoE:

```text
Laptop Ethernet  ->  PoE injector/switch  ->  camera RJ45
```

If using external Hirose/I/O power, PoE injector is not needed.

---

## 13. Error handling requirements

`DahengCameraService` must provide clear errors:

```text
SDK not installed
GxIAPINET.dll not found
No camera found
Camera found but cannot open
Camera IP not reachable
Acquisition failed
Frame timeout
Unsupported pixel format
Failed to convert image buffer
```

Do not show raw SDK error codes only.  
Wrap them in human-readable exceptions.

Example:

```csharp
throw new CameraException(
    "No Daheng camera found. Check power, Ethernet connection, IP configuration, and firewall."
);
```

---

## 14. Suggested custom exceptions

```csharp
namespace CassetteDatasetCapture.Camera;

public sealed class CameraException : Exception
{
    public CameraException(string message) : base(message)
    {
    }

    public CameraException(string message, Exception innerException)
        : base(message, innerException)
    {
    }
}
```

---

## 15. Configuration file for camera settings

Add project-level camera settings:

```json
{
  "camera": {
    "mode": "Daheng",
    "serial_number": "",
    "exposure_us": 8000,
    "gain": 0,
    "pixel_format": "Mono8",
    "trigger_mode": "Off",
    "frame_timeout_ms": 2000
  }
}
```

If `serial_number` is empty, open the first available Daheng camera.

---

## 16. UI additions for real camera mode

Main UI should have:

```text
[Camera mode: Mock / Daheng]
[Connect camera]
[Start live]
[Stop live]
[Grab test frame]

Exposure us: [8000]
Gain:        [0]
[Apply camera settings]

Camera status:
  Connected / Not connected
  Serial number
  Model
  IP address
  Pixel format
```

For MVP, only Mock mode is required.  
For Phase 2, Daheng mode should be added.

---

## 17. Live-view implementation

Avoid blocking UI thread.

Recommended WinForms approach:

- use a `System.Windows.Forms.Timer` for live-view refresh;
- timer interval: 100–200 ms;
- on each tick, call `GrabFrame()`;
- display scaled Bitmap in PictureBox;
- dispose old Bitmaps to avoid memory leaks.

For high-performance live-view later, use SDK callbacks.  
For MVP / dataset capture, timer-based polling is acceptable.

---

## 18. Image conversion requirements

The Daheng camera is mono.

Preferred MVP pipeline:

```text
SDK frame -> Mono8 buffer -> 8-bit grayscale Bitmap -> PNG
```

If SDK returns Mono12:

```text
Mono12 -> normalize or shift to Mono8 -> Bitmap -> PNG
```

Do not silently save incorrectly interpreted pixel data.

The saved PNG must visually match Galaxy Viewer output.

---

## 19. Frame saving requirements

For each capture:

```text
1. Grab frame.
2. Save image to PNG.
3. Write labels.csv row.
4. Write labels.jsonl row.
5. Update progress.json.
```

If frame grabbing fails, do not write label rows.

---

## 20. DahengCameraService skeleton

Codex should implement this class only after inspecting SDK samples.

```csharp
using System.Drawing;

namespace CassetteDatasetCapture.Camera;

public sealed class DahengCameraService : ICameraService
{
    public bool IsConnected { get; private set; }
    public bool IsLive { get; private set; }

    public double ExposureUs { get; set; } = 8000;
    public double Gain { get; set; } = 0;

    public string? SerialNumber { get; set; }
    public int FrameTimeoutMs { get; set; } = 2000;

    public void Connect()
    {
        // TODO:
        // 1. Initialize GxIAPINET / Galaxy SDK.
        // 2. Enumerate devices.
        // 3. Select by SerialNumber if provided, otherwise first camera.
        // 4. Open device.
        // 5. Apply basic camera settings.
        //
        // Important:
        // Use code from the installed Galaxy SDK C# sample.
        // Do not invent API calls.
        throw new NotImplementedException("Implement after inspecting Galaxy SDK C# samples.");
    }

    public void Disconnect()
    {
        StopLive();

        // TODO:
        // Close device and uninitialize SDK if required.

        IsConnected = false;
    }

    public void StartLive()
    {
        if (!IsConnected)
            Connect();

        // TODO:
        // Start acquisition / stream.

        IsLive = true;
    }

    public void StopLive()
    {
        if (!IsLive)
            return;

        // TODO:
        // Stop acquisition / stream.

        IsLive = false;
    }

    public Bitmap GrabFrame()
    {
        if (!IsConnected)
            Connect();

        // TODO:
        // 1. Ensure acquisition is started.
        // 2. Grab image with timeout.
        // 3. Convert to Bitmap.
        // 4. Return Bitmap.
        //
        // Must throw CameraException on failure.

        throw new NotImplementedException("Implement after inspecting Galaxy SDK C# samples.");
    }

    public void Dispose()
    {
        Disconnect();
    }
}
```

---

## 21. What Codex should inspect in sample code

When real SDK is available, Codex should inspect sample code and identify:

```text
namespace used for SDK
factory initialization call
device enumeration API
device open API
stream open/start API
single frame grab API
callback frame grab API
feature access API
image buffer access API
Mono8 conversion API
device close API
SDK uninitialization call
```

Add comments in `DahengCameraService` mapping each app-level method to SDK calls.

---

## 22. Features to set via SDK

The following features are usually GenICam-style node names.

Exact names must be confirmed through SDK docs or Galaxy Viewer.

Likely feature names:

```text
ExposureAuto
ExposureTime
GainAuto
Gain
TriggerMode
AcquisitionMode
PixelFormat
Width
Height
OffsetX
OffsetY
```

For MVP:

```text
ExposureAuto = Off
GainAuto     = Off
TriggerMode  = Off
PixelFormat  = Mono8
```

Do not crash if a feature is unavailable.  
Check feature availability / writability first if SDK supports that.

---

## 23. Testing real SDK integration

Manual test checklist:

```text
[ ] Galaxy Viewer sees camera.
[ ] Galaxy Viewer can start acquisition.
[ ] C# sample from SDK builds.
[ ] C# sample from SDK grabs image.
[ ] CassetteDatasetCapture can connect camera.
[ ] Camera model and serial are displayed.
[ ] Live-view works.
[ ] Exposure change affects image.
[ ] Gain change affects image.
[ ] Capture saves PNG.
[ ] Saved PNG visually matches live-view.
[ ] labels.csv/jsonl row is written only after image is saved.
[ ] Disconnect/reconnect works.
[ ] App closes without hanging camera stream.
```

---

## 24. Deployment notes

For deployment to another Windows machine:

1. Install Galaxy Windows Runtime SDK or full Galaxy Windows SDK.
2. Confirm `GxIAPINET.dll` dependencies are available.
3. Confirm camera is visible in Galaxy Viewer.
4. Copy application files.
5. Run app.
6. Select Daheng camera mode.
7. Connect.

Do not assume that simply copying `GxIAPINET.dll` is enough; native Galaxy SDK DLLs and drivers may also be required.

---

## 25. When to use Galaxy Viewer vs custom app

Use Galaxy Viewer for:

```text
initial camera detection
IP setup
focus setup
exposure/gain tuning
checking image quality
saving a few manual test images
```

Use custom app for:

```text
planned dataset capture
automatic labels
capture_plan.json workflow
progress tracking
cross-slot annotation
operator-guided acquisition
```

Galaxy Viewer is not sufficient for the full dataset task because it does not manage capture plans and ML labels.

---

## 26. Sources checked

Official / vendor pages used to prepare this document:

```text
Daheng Imaging Software page:
https://en.daheng-imaging.com/list-59-1.html

Daheng Imaging Manuals page:
https://en.daheng-imaging.com/list-60-1.html

VA Imaging SDK overview:
https://va-imaging.com/collections/software-development-kit-daheng-imaging-cameras

VA Imaging C#/.NET acquisition guide:
https://va-imaging.com/blogs/machine-vision-knowledge-center/how-to-compile-a-example-program-to-acquire-images-in-visual-studio

VA Imaging Galaxy Viewer guide:
https://va-imaging.com/blogs/machine-vision-knowledge-center/daheng-galaxy-viewer-to-program-our-industrial-cameras

A3 / Automate quickstart:
https://www.automate.org/vision/tech-papers/quickstart-how-to-install-a-machine-vision-camera-and-acquire-an-image-in-5-steps
```

Access date:

```text
2026-06-21
```

---

## 27. Final instruction to Codex

Do not implement `DahengCameraService` blindly.

First:

1. Build the MVP with `MockCameraService`.
2. Install Galaxy Windows SDK.
3. Confirm camera works in Galaxy Viewer.
4. Build and run the SDK's own C#/.NET sample.
5. Only then implement `DahengCameraService` by adapting the working SDK sample.

Preserve the `ICameraService` boundary so the rest of the application remains independent from Galaxy SDK.
