using CassetteDatasetCapture.Camera;
using CassetteDatasetCapture.CapturePlan;
using CassetteDatasetCapture.Dataset;
using CassetteDatasetCapture.Model;

namespace CassetteDatasetCapture.UI;

public sealed class MainForm : Form
{
    private const int SidebarWidth = 360;
    private const int SidebarControlWidth = 320;
    private const int BrowseButtonWidth = 84;

    private readonly ComboBox _cameraMode = new()
    {
        DropDownStyle = ComboBoxStyle.DropDownList,
        Width = SidebarControlWidth
    };

    private readonly TextBox _planPath = new() { Width = SidebarControlWidth, Text = "capture_plan.json" };
    private readonly TextBox _datasetRoot = new() { Width = SidebarControlWidth, Text = Path.Combine(Environment.CurrentDirectory, "dataset_root") };
    private readonly TextBox _operatorName = new() { Width = SidebarControlWidth, Text = Environment.UserName };
    private readonly TextBox _exposureUs = new() { Width = SidebarControlWidth, Text = "8000" };
    private readonly TextBox _gain = new() { Width = SidebarControlWidth, Text = "0" };

    private readonly Button _browsePlan = CreateSidebarButton("Обзор");
    private readonly Button _browseDataset = CreateSidebarButton("Обзор");
    private readonly Button _loadPlan = CreateSidebarButton("Загрузить план");
    private readonly Button _connect = CreateSidebarButton("Подключить камеру");
    private readonly Button _startLive = CreateSidebarButton("Запустить просмотр");
    private readonly Button _stopLive = CreateSidebarButton("Остановить просмотр");
    private readonly Button _capture = CreateSidebarButton("Сделать снимок");
    private readonly Button _retake = CreateSidebarButton("Переснять");
    private readonly Button _skip = CreateSidebarButton("Пропустить");
    private readonly Button _prev = CreateSidebarButton("Назад");
    private readonly Button _next = CreateSidebarButton("Далее");

    private readonly Label _current = new()
    {
        Dock = DockStyle.Top,
        AutoSize = true,
        Font = new Font("Segoe UI", 12, FontStyle.Bold)
    };

    private readonly Label _instruction = new()
    {
        Dock = DockStyle.Top,
        AutoSize = true,
        Font = new Font("Segoe UI", 10, FontStyle.Regular)
    };

    private readonly Label _status = new() { Dock = DockStyle.Bottom, Height = 28, Text = "Готово" };

    private readonly PictureBox _preview = new()
    {
        Dock = DockStyle.Top,
        Height = 460,
        SizeMode = PictureBoxSizeMode.Zoom,
        BackColor = Color.Black
    };

    private readonly Panel _slotMap = new()
    {
        Dock = DockStyle.Fill,
        AutoScroll = true,
        Padding = new Padding(8)
    };

    private readonly Panel _details = new()
    {
        Dock = DockStyle.Bottom,
        Height = 110,
        Padding = new Padding(8),
        BackColor = Color.FromArgb(245, 247, 250)
    };

    private readonly System.Windows.Forms.Timer _liveTimer = new() { Interval = 150 };

    private ICameraService _camera = new DahengCameraService();
    private DatasetWriter? _writer;
    private ProgressStore? _progressStore;
    private CapturePlan.CapturePlan? _plan;
    private LastCapture? _lastCapture;
    private int _currentConfigIndex;
    private int _shotIndex = 1;
    private Bitmap? _lastFrame;
    private string _activeCameraMode = "Daheng";
    private bool _datasetCompleted;

    public MainForm()
    {
        Text = "CassetteDatasetCapture";
        Width = 1800;
        Height = 1020;

        _cameraMode.Items.AddRange(["Daheng", "Тестовая"]);
        _cameraMode.SelectedIndex = 0;
        _cameraMode.SelectedIndexChanged += (_, _) => RecreateCamera(force: true);

        var sidebar = CreateSidebar();
        _details.Controls.Add(_instruction);
        _details.Controls.Add(_current);

        Controls.Add(_slotMap);
        Controls.Add(_details);
        Controls.Add(_preview);
        Controls.Add(sidebar);
        Controls.Add(_status);

        _loadPlan.Click += (_, _) => LoadPlan();
        _browsePlan.Click += (_, _) => BrowsePlan();
        _browseDataset.Click += (_, _) => BrowseDatasetRoot();
        _connect.Click += (_, _) => ConnectCamera();
        _startLive.Click += (_, _) => StartLive();
        _stopLive.Click += (_, _) => StopLive();
        _capture.Click += (_, _) => CaptureCurrent();
        _retake.Click += (_, _) => RetakeLastCapture();
        _skip.Click += (_, _) => SkipCurrent();
        _prev.Click += (_, _) => PreviousConfig();
        _next.Click += (_, _) => NextConfig();
        _liveTimer.Tick += (_, _) => RefreshLive();
        FormClosing += (_, _) => Cleanup();

        UpdateUi();
    }

    private FlowLayoutPanel CreateSidebar()
    {
        var sidebar = new FlowLayoutPanel
        {
            Dock = DockStyle.Left,
            Width = SidebarWidth,
            Padding = new Padding(12),
            AutoScroll = true,
            FlowDirection = FlowDirection.TopDown,
            WrapContents = false
        };

        AddField(sidebar, "Режим камеры", _cameraMode);
        AddField(sidebar, "Путь к конфигурации", CreatePathField(_planPath, _browsePlan));
        AddField(sidebar, "Папка датасета", CreatePathField(_datasetRoot, _browseDataset));
        AddField(sidebar, "Оператор", _operatorName);
        AddField(sidebar, "Экспозиция, мкс", _exposureUs);
        AddField(sidebar, "Усиление", _gain);

        sidebar.Controls.Add(_loadPlan);
        sidebar.Controls.Add(_connect);
        sidebar.Controls.Add(_startLive);
        sidebar.Controls.Add(_stopLive);
        sidebar.Controls.Add(_capture);
        sidebar.Controls.Add(_retake);
        sidebar.Controls.Add(_skip);
        sidebar.Controls.Add(_prev);
        sidebar.Controls.Add(_next);

        return sidebar;
    }

    private static void AddField(FlowLayoutPanel parent, string title, Control control)
    {
        parent.Controls.Add(new Label
        {
            Text = title,
            Width = SidebarControlWidth,
            Height = 18,
            Margin = new Padding(0, 8, 0, 2)
        });

        control.Margin = new Padding(0, 0, 0, 4);
        parent.Controls.Add(control);
    }

    private static Control CreatePathField(TextBox textBox, Button browseButton)
    {
        textBox.Margin = new Padding(0, 0, 4, 0);
        textBox.Dock = DockStyle.Fill;

        browseButton.Width = BrowseButtonWidth;
        browseButton.Height = 30;
        browseButton.Margin = new Padding(0);
        browseButton.Dock = DockStyle.Fill;

        var row = new TableLayoutPanel
        {
            Width = SidebarControlWidth,
            AutoSize = true,
            ColumnCount = 2,
            RowCount = 1,
            Margin = new Padding(0, 0, 0, 4)
        };
        row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        row.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, BrowseButtonWidth));
        row.Controls.Add(textBox, 0, 0);
        row.Controls.Add(browseButton, 1, 0);
        return row;
    }

    private static Button CreateSidebarButton(string text) => new()
    {
        Text = text,
        Width = SidebarControlWidth,
        Height = 32,
        Margin = new Padding(0, 8, 0, 0)
    };

    private void LoadPlan()
    {
        try
        {
            var planPath = ResolvePlanPath(_planPath.Text);
            _planPath.Text = planPath;
            _plan = CapturePlanLoader.Load(planPath);

            var errors = CapturePlanValidator.Validate(_plan);
            if (errors.Count > 0)
            {
                throw new InvalidDataException(string.Join(Environment.NewLine, errors));
            }

            _currentConfigIndex = 0;
            _shotIndex = 1;
            _lastCapture = null;
            _datasetCompleted = false;
            _writer = new DatasetWriter(new DatasetPaths { Root = ResolveAbsolutePath(_datasetRoot.Text) });
            _datasetRoot.Text = _writer.Paths.Root;
            _writer.EnsureLayout();
            _progressStore = new ProgressStore(new ProgressState
            {
                Project = _plan.Project,
                CurrentConfigId = _plan.Configs.FirstOrDefault()?.Id ?? string.Empty,
                Configs = _plan.Configs.ToDictionary(c => c.Id, _ => new ProgressItem())
            });
            _progressStore.Save(Path.Combine(_writer.Paths.Root, "progress.json"));
            ApplyCameraSettings();
            UpdateUi();
            SetStatus($"План загружен: {_plan.Project}");
        }
        catch (Exception ex)
        {
            SetStatus(ex.Message);
        }
    }

    private void BrowsePlan()
    {
        using var dialog = new OpenFileDialog
        {
            Title = "Выберите файл конфигурации",
            Filter = "JSON files (*.json)|*.json|All files (*.*)|*.*",
            CheckFileExists = true,
            InitialDirectory = GetInitialDirectory(_planPath.Text),
            FileName = Path.GetFileName(_planPath.Text)
        };

        if (dialog.ShowDialog(this) == DialogResult.OK)
        {
            _planPath.Text = dialog.FileName;
        }
    }

    private void BrowseDatasetRoot()
    {
        using var dialog = new FolderBrowserDialog
        {
            Description = "Выберите папку датасета",
            UseDescriptionForTitle = true,
            ShowNewFolderButton = true,
            SelectedPath = GetInitialDirectory(_datasetRoot.Text)
        };

        if (dialog.ShowDialog(this) == DialogResult.OK && !string.IsNullOrWhiteSpace(dialog.SelectedPath))
        {
            _datasetRoot.Text = dialog.SelectedPath;
        }
    }

    private void ConnectCamera()
    {
        try
        {
            RecreateCamera();
            ApplyCameraSettings();
            _camera.Connect();
            SetStatus(_activeCameraMode == "Daheng" ? "Камера Daheng подключена" : "Подключена тестовая камера");
            UpdateUi();
        }
        catch (Exception ex)
        {
            SetStatus(ex.Message);
        }
    }

    private void RecreateCamera(bool force = false)
    {
        var selectedMode = _cameraMode.SelectedItem?.ToString() == "Тестовая" ? "Тестовая" : "Daheng";
        if (!force && _activeCameraMode == selectedMode && _camera.IsConnected)
        {
            return;
        }

        _liveTimer.Stop();
        _camera.Dispose();
        _activeCameraMode = selectedMode;
        _camera = selectedMode == "Тестовая" ? new MockCameraService() : new DahengCameraService();
    }

    private void ApplyCameraSettings()
    {
        if (double.TryParse(_exposureUs.Text, out var exposure))
        {
            _camera.ExposureUs = exposure;
        }

        if (double.TryParse(_gain.Text, out var gain))
        {
            _camera.Gain = gain;
        }
    }

    private void StartLive()
    {
        try
        {
            RecreateCamera();
            ApplyCameraSettings();
            _camera.StartLive();
            _liveTimer.Start();
            SetStatus("Просмотр запущен");
        }
        catch (Exception ex)
        {
            SetStatus(ex.Message);
        }
    }

    private void StopLive()
    {
        _liveTimer.Stop();
        _camera.StopLive();
        SetStatus("Просмотр остановлен");
    }

    private void RefreshLive()
    {
        if (!_camera.IsConnected) return;
        RenderFrame(_camera.GrabFrame());
    }

    private void CaptureCurrent()
    {
        if (_datasetCompleted)
        {
            SetStatus("Датасет завершён. Все конфигурации обработаны.");
            return;
        }

        if (_plan is null || _writer is null || _progressStore is null)
        {
            SetStatus("Сначала загрузите план");
            return;
        }

        try
        {
            var cfg = CurrentConfig;
            RecreateCamera();
            ApplyCameraSettings();
            using var frame = _camera.GrabFrame();
            RenderFrame(frame);

            var record = SaveCapture(frame, cfg, _shotIndex, "accepted", string.Empty);
            _lastCapture = new LastCapture(_currentConfigIndex, cfg.Id, record.ImagePath, record.ShotIndex);

            var completedShots = _shotIndex;
            var isConfigDone = completedShots >= Math.Max(1, _plan.ShotsPerConfig);
            MarkCurrent(isConfigDone ? "done" : "in_progress", completedShots);
            if (isConfigDone)
            {
                AdvanceAfterCurrentConfig();
            }
            else
            {
                _shotIndex++;
                UpdateUi();
            }
        }
        catch (Exception ex)
        {
            SetStatus(ex.Message);
        }
    }

    private void RetakeLastCapture()
    {
        if (_plan is null || _writer is null || _progressStore is null)
        {
            SetStatus("Сначала загрузите план");
            return;
        }

        if (_lastCapture is null)
        {
            SetStatus("Нет снимка для пересъёмки.");
            return;
        }

        try
        {
            var target = _lastCapture;
            if (target.ConfigIndex < 0 || target.ConfigIndex >= _plan.Configs.Count)
            {
                SetStatus("Не удалось определить конфигурацию для пересъёмки.");
                return;
            }

            _writer.MarkImageRejected(target.ImagePath, "Переснято оператором");
            _currentConfigIndex = target.ConfigIndex;
            _datasetCompleted = false;
            var cfg = _plan.Configs[target.ConfigIndex];
            var replacementShotIndex = target.ShotIndex;

            RecreateCamera();
            ApplyCameraSettings();
            using var frame = _camera.GrabFrame();
            RenderFrame(frame);

            var record = SaveCapture(frame, cfg, replacementShotIndex, "accepted", "Пересъёмка");
            _lastCapture = new LastCapture(target.ConfigIndex, cfg.Id, record.ImagePath, record.ShotIndex);

            var shotsDone = GetShotsDone(cfg.Id);
            if (shotsDone == 0)
            {
                shotsDone = Math.Min(target.ShotIndex, Math.Max(1, _plan.ShotsPerConfig));
            }

            _shotIndex = Math.Min(shotsDone + 1, Math.Max(1, _plan.ShotsPerConfig));
            MarkCurrent(shotsDone >= Math.Max(1, _plan.ShotsPerConfig) ? "done" : "in_progress", shotsDone);
            UpdateUi();
            SetStatus("Снимок переснят. Предыдущая запись помечена как rejected.");
        }
        catch (Exception ex)
        {
            SetStatus(ex.Message);
        }
    }

    private void SkipCurrent()
    {
        if (_datasetCompleted)
        {
            SetStatus("Датасет уже завершён.");
            return;
        }

        MarkCurrent("skipped", Math.Max(0, _shotIndex - 1));
        AdvanceAfterCurrentConfig();
    }

    private void PreviousConfig()
    {
        if (_plan is null || _plan.Configs.Count == 0) return;
        _datasetCompleted = false;
        _currentConfigIndex = Math.Max(0, _currentConfigIndex - 1);
        _shotIndex = 1;
        UpdateUi();
    }

    private void NextConfig()
    {
        if (_plan is null || _plan.Configs.Count == 0) return;
        if (_currentConfigIndex >= _plan.Configs.Count - 1)
        {
            CompleteDataset();
            return;
        }

        _currentConfigIndex++;
        _shotIndex = 1;
        _datasetCompleted = false;
        UpdateUi();
    }

    private void AdvanceAfterCurrentConfig()
    {
        if (_plan is null || _currentConfigIndex >= _plan.Configs.Count - 1)
        {
            CompleteDataset();
            return;
        }

        NextConfig();
    }

    private void CompleteDataset()
    {
        if (_datasetCompleted) return;
        _datasetCompleted = true;
        _shotIndex = 1;
        UpdateUi();
        SetStatus("Датасет завершён. Все конфигурации обработаны.");
        MessageBox.Show(this, "Датасет завершён. Все конфигурации обработаны.", "Съёмка завершена", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }

    private DatasetRecord SaveCapture(Bitmap frame, CaptureConfig cfg, int shotIndex, string status, string notes)
    {
        var ts = DateTimeOffset.Now;
        var rel = Path.Combine("images", $"{_plan!.CassetteSizeMm}mm", cfg.Id, $"{cfg.Id}_{ts:yyyyMMdd_HHmmss}_{shotIndex:000}.png");
        var abs = Path.Combine(_writer!.Paths.Root, rel);
        Directory.CreateDirectory(Path.GetDirectoryName(abs)!);
        frame.Save(abs, System.Drawing.Imaging.ImageFormat.Png);

        var record = new DatasetRecord
        {
            ImagePath = rel.Replace('\\', '/'),
            CassetteSizeMm = _plan.CassetteSizeMm,
            SlotCount = _plan.SlotCount,
            ConfigId = cfg.Id,
            ShotIndex = shotIndex,
            NormalOccupancy = cfg.NormalOccupancy,
            BlockedSlots = cfg.BlockedSlots,
            SlotStates = cfg.SlotStates,
            Anomalies = cfg.Anomalies,
            ImageQuality = status == "rejected" ? "rejected" : ImageQuality.Ok.ToString().ToLowerInvariant(),
            ExposureUs = _camera.ExposureUs,
            Gain = _camera.Gain,
            Timestamp = ts,
            OperatorName = _operatorName.Text,
            Status = status,
            Notes = notes
        };

        _writer.Append(record);
        return record;
    }

    private int GetShotsDone(string configId)
    {
        return _progressStore?.State.Configs.TryGetValue(configId, out var item) == true ? item.ShotsDone : 0;
    }

    private void MarkCurrent(string progressStatus, int shotsDone)
    {
        if (_progressStore is null || _plan is null || _writer is null) return;
        _progressStore.Set(CurrentConfig.Id, progressStatus, shotsDone);
        _progressStore.Save(Path.Combine(_writer.Paths.Root, "progress.json"));
    }

    private void RenderFrame(Bitmap frame)
    {
        _lastFrame?.Dispose();
        _lastFrame = new Bitmap(frame);
        _preview.Image?.Dispose();
        _preview.Image = new Bitmap(_lastFrame);
    }

    private void UpdateUi()
    {
        if (_plan is null || _plan.Configs.Count == 0)
        {
            _current.Text = "План не загружен";
            _instruction.Text = string.Empty;
            _slotMap.Controls.Clear();
            _next.Enabled = false;
            _capture.Enabled = false;
            _retake.Enabled = false;
            _skip.Enabled = false;
            return;
        }

        var cfg = CurrentConfig;
        _current.Text = $"Конфигурация: {cfg.Id} | {(_currentConfigIndex + 1)}/{_plan.Configs.Count} | Снимок {_shotIndex}/{Math.Max(1, _plan.ShotsPerConfig)}";
        _instruction.Text = cfg.OperatorInstruction;
        Text = $"CassetteDatasetCapture - {cfg.Id}";
        _next.Enabled = !_datasetCompleted && _currentConfigIndex < _plan.Configs.Count - 1;
        _capture.Enabled = !_datasetCompleted;
        _retake.Enabled = _lastCapture is not null;
        _skip.Enabled = !_datasetCompleted;
        RenderSlotMap(cfg);
    }

    private void RenderSlotMap(CaptureConfig cfg)
    {
        _slotMap.SuspendLayout();
        _slotMap.Controls.Clear();

        var grid = new TableLayoutPanel
        {
            Dock = DockStyle.Top,
            AutoSize = true,
            ColumnCount = 5
        };

        var total = _plan?.SlotCount ?? cfg.SlotStates.Length;
        for (var i = 0; i < 5; i++)
        {
            grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 20));
        }

        var stateChars = cfg.SlotStates.PadRight(total, '0');
        var occChars = cfg.NormalOccupancy.PadRight(total, '0');
        var blockedChars = cfg.BlockedSlots.PadRight(total, '0');

        for (var i = 0; i < total; i++)
        {
            var slotPanel = CreateSlotCell(i + 1, ParseState(stateChars[i]), occChars[i] == '1', blockedChars[i] == '1');
            grid.Controls.Add(slotPanel, i % 5, i / 5);
        }

        _slotMap.Controls.Add(grid);
        _slotMap.ResumeLayout();
    }

    private static Panel CreateSlotCell(int slotNumber, SlotState state, bool occupancy, bool blocked)
    {
        var panel = new Panel
        {
            Width = 68,
            Height = 64,
            Margin = new Padding(4),
            BorderStyle = BorderStyle.FixedSingle
        };

        var color = state switch
        {
            SlotState.Empty => Color.Gainsboro,
            SlotState.OccupiedOk => Color.FromArgb(180, 230, 180),
            SlotState.CrossSlot => Color.FromArgb(255, 200, 120),
            SlotState.ShiftedInSlot => Color.FromArgb(170, 210, 255),
            SlotState.DoubleLoadedSuspect => Color.FromArgb(255, 140, 140),
            SlotState.Uncertain => Color.Khaki,
            _ => Color.Gainsboro
        };

        panel.BackColor = blocked ? Color.FromArgb(220, color) : color;

        var label = new Label
        {
            Dock = DockStyle.Fill,
            TextAlign = ContentAlignment.MiddleCenter,
            Font = new Font("Segoe UI", 10, FontStyle.Bold),
            Text = slotNumber.ToString()
        };

        var tag = new Label
        {
            Dock = DockStyle.Bottom,
            Height = 16,
            TextAlign = ContentAlignment.MiddleCenter,
            Font = new Font("Segoe UI", 7, FontStyle.Regular),
            Text = blocked ? "B" : occupancy ? "O" : "-"
        };

        panel.Controls.Add(label);
        panel.Controls.Add(tag);
        return panel;
    }

    private static SlotState ParseState(char value) => value switch
    {
        '0' => SlotState.Empty,
        '1' => SlotState.OccupiedOk,
        '2' => SlotState.CrossSlot,
        '3' => SlotState.ShiftedInSlot,
        '4' => SlotState.DoubleLoadedSuspect,
        '5' => SlotState.Uncertain,
        _ => SlotState.Uncertain
    };

    private CaptureConfig CurrentConfig => _plan!.Configs[_currentConfigIndex];

    private void SetStatus(string text) => _status.Text = text;

    private void Cleanup()
    {
        _liveTimer.Stop();
        _camera.Dispose();
        _lastFrame?.Dispose();
    }

    private string ResolvePlanPath(string input)
    {
        if (Path.IsPathRooted(input))
        {
            return input;
        }

        var baseDir = AppContext.BaseDirectory;
        var candidates = new[]
        {
            Path.GetFullPath(Path.Combine(baseDir, input)),
            Path.GetFullPath(Path.Combine(Environment.CurrentDirectory, input)),
            Path.GetFullPath(Path.Combine(baseDir, "..", "..", "..", input))
        };

        return candidates.FirstOrDefault(File.Exists) ?? candidates[0];
    }

    private static string ResolveAbsolutePath(string input)
    {
        return Path.IsPathRooted(input) ? input : Path.GetFullPath(Path.Combine(Environment.CurrentDirectory, input));
    }

    private static string GetInitialDirectory(string path)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            return AppContext.BaseDirectory;
        }

        var absolute = Path.IsPathRooted(path)
            ? Path.GetFullPath(path)
            : Path.GetFullPath(Path.Combine(Environment.CurrentDirectory, path));

        return Directory.Exists(absolute) ? absolute : Path.GetDirectoryName(absolute) ?? AppContext.BaseDirectory;
    }

    private sealed record LastCapture(int ConfigIndex, string ConfigId, string ImagePath, int ShotIndex);
}
