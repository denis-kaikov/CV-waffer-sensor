# CassetteDatasetCapture — техническое задание для Codex

## 1. Назначение проекта

Нужно разработать Windows-приложение на C# для съёмки датасета с промышленной камеры Daheng MER2-1220-9GM-P.

Камера устанавливается под кассетой для пластин 100 / 150 / 200 мм.  
Оператор должен по заранее заданному плану собирать разные конфигурации заполненности кассеты, а программа должна делать снимки и автоматически сохранять корректную разметку.

Главная цель датасета — обучение модели, которая по изображению определяет карту заполненности кассеты и аномальные состояния пластин.

---

## 2. Ключевая идея

Оператор НЕ должен вручную размечать каждый снимок.

Вместо этого используется заранее подготовленный файл:

```text
capture_plan.json
```

В нём перечислены все конфигурации кассеты, которые нужно отснять.

Программа показывает оператору текущую конфигурацию:

```text
cfg_000042

Кассета: 150 мм
Поставить пластины в слоты: 3, 7, 12, 18

Аномалия:
пластина между слотами 21 и 22

[Сделать снимок]
```

Оператор физически собирает кассету, нажимает Capture, программа делает снимок и автоматически сохраняет изображение + разметку.

---

## 3. Целевая платформа

- OS: Windows 10 / Windows 11
- Язык: C#
- Framework: .NET 8
- UI: WinForms
- Камера: Daheng MER2-1220-9GM-P
- SDK: Daheng Galaxy SDK for Windows
- Формат изображений: PNG на MVP-этапе, позже можно добавить TIFF
- Форматы разметки: CSV + JSONL
- Основной режим камеры: ручной capture по кнопке

---

## 4. Причина выбора C# / WinForms

Приложение будет использоваться оператором на Windows-ноутбуке.  
WinForms проще и быстрее для MVP, чем WPF, и достаточно надёжен для лабораторной/производственной утилиты.

Важные цели:

- минимальное количество действий для оператора;
- возможность продолжить съёмку после паузы;
- контроль, какие конфигурации уже сняты;
- сохранение полной разметки без ручной постобработки;
- возможность заменить mock-камеру на реальную Daheng-камеру.

---

## 5. Аппаратная схема

Камера Daheng MER2-1220-9GM-P является GigE/PoE камерой.

Возможны два варианта питания:

### Вариант A — через PoE

```text
Ноутбук/ПК -> Ethernet -> PoE-инжектор или PoE-свитч -> Ethernet -> камера
```

### Вариант B — через отдельное питание

```text
Ноутбук/ПК -> обычный Ethernet -> камера
Блок питания 12–24V -> Hirose/I/O кабель -> камера
```

Если используется отдельный провод питания через Hirose/I/O, PoE-инжектор не нужен.

Не подавать одновременно PoE и внешнее питание, если в документации к конкретной ревизии камеры не указано, что это разрешено.

---

## 6. Основные сущности проекта

### 6.1 Кассета

Кассета имеет:

- размер: 100 / 150 / 200 мм;
- количество слотов;
- список состояний слотов;
- набор аномалий.

### 6.2 Слот

Каждый слот имеет состояние:

```csharp
public enum SlotState
{
    Empty = 0,
    OccupiedOk = 1,
    CrossSlot = 2,
    ShiftedInSlot = 3,
    DoubleLoadedSuspect = 4,
    Uncertain = 5
}
```

Значения:

| Значение | Название | Описание |
|---:|---|---|
| 0 | Empty | слот пустой |
| 1 | OccupiedOk | пластина стоит нормально |
| 2 | CrossSlot | пластина стоит между двумя слотами |
| 3 | ShiftedInSlot | пластина в своём слоте, но смещена |
| 4 | DoubleLoadedSuspect | подозрение на две пластины |
| 5 | Uncertain | оператор/проверяющий не уверен |

### 6.3 Cross-slot anomaly

Особый важный случай:

> одна сторона пластины находится в одном слоте, другая сторона — в соседнем слоте.

Например, одна пластина стоит между слотами 8 и 9.

Это НЕ должно размечаться как две нормальные пластины.

Для такого случая:

```text
normal_occupancy = 0 для слотов 8 и 9
blocked_slots    = 1 для слотов 8 и 9
slot_states      = 2 для слотов 8 и 9
```

И дополнительно создаётся anomaly:

```json
{
  "type": "cross_slot_plate",
  "slots": [8, 9],
  "severity": 2
}
```

---

## 7. Разметка

Нужно сохранять несколько разных представлений разметки.

### 7.1 normal_occupancy

Строка из 0/1.  
Единица только там, где пластина стоит правильно.

Пример:

```text
0000100000000000000000000
```

### 7.2 blocked_slots

Строка из 0/1.  
Единица там, где слот физически занят или заблокирован любой пластиной, включая cross-slot.

Пример:

```text
0000100110000000000000000
```

### 7.3 slot_states

Строка из чисел, соответствующих SlotState.

Пример:

```text
0000100220000000000000000
```

Расшифровка:

```text
1 = OccupiedOk
2 = CrossSlot
```

### 7.4 anomalies_json

JSON-массив с описанием аномалий.

Пример:

```json
[
  {
    "type": "cross_slot_plate",
    "slots": [8, 9],
    "severity": 2,
    "note": "Одна пластина между слотами 8 и 9"
  }
]
```

---

## 8. Форматы выходных файлов

### 8.1 Структура датасета

Пример итоговой структуры:

```text
dataset_root/
  capture_plan.json
  progress.json
  labels.csv
  labels.jsonl

  images/
    100mm/
      cfg_000001/
        cfg_000001_20260621_120001_001.png
        cfg_000001_20260621_120002_002.png

    150mm/
      cfg_000042/
        cfg_000042_20260621_121501_001.png

    200mm/
      cfg_000100/
        cfg_000100_20260621_130010_001.png

  rejected/
    ...
```

### 8.2 labels.csv

CSV-заголовок:

```csv
image_path,cassette_size_mm,slot_count,config_id,shot_index,normal_occupancy,blocked_slots,slot_states,anomalies_json,image_quality,exposure_us,gain,timestamp,operator_name,status,notes
```

Пример строки:

```csv
"images/150mm/cfg_000050/cfg_000050_20260621_121501_001.png",150,25,"cfg_000050",1,"0000000000000000000000000","0000000110000000000000000","0000000220000000000000000","[{""type"":""cross_slot_plate"",""slots"":[8,9],""severity"":2}]","ok",8000,0,"2026-06-21T12:15:01.0000000+02:00","operator","accepted",""
```

### 8.3 labels.jsonl

Каждая строка — отдельный JSON-объект.

Пример:

```json
{"image_path":"images/150mm/cfg_000050/cfg_000050_20260621_121501_001.png","cassette_size_mm":150,"slot_count":25,"config_id":"cfg_000050","shot_index":1,"normal_occupancy":"0000000000000000000000000","blocked_slots":"0000000110000000000000000","slot_states":"0000000220000000000000000","anomalies":[{"type":"cross_slot_plate","slots":[8,9],"severity":2}],"image_quality":"ok","exposure_us":8000,"gain":0,"timestamp":"2026-06-21T12:15:01.0000000+02:00","operator_name":"operator","status":"accepted","notes":""}
```

---

## 9. capture_plan.json

### 9.1 Назначение

`capture_plan.json` — заранее заданный план съёмки.  
Оператор идёт по этому плану и не размечает слоты вручную.

### 9.2 Пример

```json
{
  "project": "cassette_150mm_dataset_v1",
  "cassette_size_mm": 150,
  "slot_count": 25,
  "shots_per_config": 3,
  "default_exposure_us": 8000,
  "default_gain": 0,
  "configs": [
    {
      "id": "cfg_000001",
      "name": "empty",
      "normal_occupancy": "0000000000000000000000000",
      "blocked_slots": "0000000000000000000000000",
      "slot_states": "0000000000000000000000000",
      "anomalies": [],
      "operator_instruction": "Оставить кассету пустой"
    },
    {
      "id": "cfg_000002",
      "name": "full",
      "normal_occupancy": "1111111111111111111111111",
      "blocked_slots": "1111111111111111111111111",
      "slot_states": "1111111111111111111111111",
      "anomalies": [],
      "operator_instruction": "Заполнить все 25 слотов"
    },
    {
      "id": "cfg_000003",
      "name": "single_slot_01",
      "normal_occupancy": "1000000000000000000000000",
      "blocked_slots": "1000000000000000000000000",
      "slot_states": "1000000000000000000000000",
      "anomalies": [],
      "operator_instruction": "Поставить пластину в слот 1"
    },
    {
      "id": "cfg_000050",
      "name": "cross_slot_08_09",
      "normal_occupancy": "0000000000000000000000000",
      "blocked_slots": "0000000110000000000000000",
      "slot_states": "0000000220000000000000000",
      "anomalies": [
        {
          "type": "cross_slot_plate",
          "slots": [8, 9],
          "severity": 2,
          "note": "Одна пластина между слотами 8 и 9"
        }
      ],
      "operator_instruction": "Установить одну пластину перекошенно: одна сторона в слот 8, другая сторона в слот 9"
    }
  ]
}
```

---

## 10. progress.json

### 10.1 Назначение

`progress.json` нужен, чтобы можно было остановить съёмку и продолжить позже.

### 10.2 Статусы

```text
pending       — ещё не снято
in_progress   — начали, но не закончили
done          — снято
skipped       — пропущено
rejected      — снято, но не использовать
needs_review  — нужна проверка
```

### 10.3 Пример

```json
{
  "project": "cassette_150mm_dataset_v1",
  "current_config_id": "cfg_000050",
  "configs": {
    "cfg_000001": {
      "status": "done",
      "shots_done": 3
    },
    "cfg_000002": {
      "status": "done",
      "shots_done": 3
    },
    "cfg_000050": {
      "status": "pending",
      "shots_done": 0
    }
  }
}
```

---

## 11. UI приложения

### 11.1 Главное окно

Элементы:

```text
[Выбрать проект]
[Загрузить capture_plan.json]
[Подключить камеру]
[Start Live]
[Stop Live]

Live-view area

Текущая конфигурация:
  ID: cfg_000050
  Cassette: 150 mm
  Slots: 25
  Shots: 0 / 3

Визуальная карта слотов:
  01 [ ]
  02 [ ]
  ...
  08 [X]
  09 [X]
  ...

Инструкция оператору:
  Установить одну пластину перекошенно: одна сторона в слот 8, другая сторона в слот 9

Аномалии:
  cross_slot_plate: slots 8, 9, severity 2

[Capture]
[Retake]
[Skip]
[Reject last shot]
[Previous config]
[Next config]
```

### 11.2 Визуальные обозначения слотов

```text
[ ] Empty
[●] OccupiedOk
[X] CrossSlot
[>] ShiftedInSlot
[!!] DoubleLoadedSuspect
[?] Uncertain
```

### 11.3 Горячие клавиши

```text
Space  — Capture
N      — Next config
P      — Previous config
R      — Retake
S      — Skip
L      — Start/Stop live
Esc    — Stop live
```

---

## 12. Структура C# проекта

```text
CassetteDatasetCapture/
  CassetteDatasetCapture.sln

  src/
    CassetteDatasetCapture/
      CassetteDatasetCapture.csproj
      Program.cs

      App/
        AppSettings.cs
        AppState.cs

      Camera/
        ICameraService.cs
        CameraFrame.cs
        MockCameraService.cs
        DahengCameraService.cs
        CameraSettings.cs

      Dataset/
        DatasetWriter.cs
        DatasetRecord.cs
        DatasetPaths.cs
        CsvWriterUtil.cs
        JsonlWriter.cs

      CapturePlan/
        CapturePlan.cs
        CaptureConfig.cs
        CapturePlanLoader.cs
        CapturePlanValidator.cs
        ProgressState.cs
        ProgressStore.cs

      Model/
        SlotState.cs
        CassetteAnnotation.cs
        CassetteAnomaly.cs
        CassetteSize.cs
        ImageQuality.cs
        CaptureStatus.cs

      UI/
        MainForm.cs
        MainForm.Designer.cs
        SlotMapControl.cs
        LiveViewControl.cs
        ConfigDetailsControl.cs

      Utils/
        TimeUtil.cs
        ImageFileNameUtil.cs
        StringMaskUtil.cs
        SafeFileWrite.cs

  tests/
    CassetteDatasetCapture.Tests/
      CassetteDatasetCapture.Tests.csproj
      CapturePlanValidatorTests.cs
      CassetteAnnotationTests.cs
      DatasetWriterTests.cs
      ProgressStoreTests.cs

  docs/
    CAMERA_SETUP.md
    DATASET_FORMAT.md
    CAPTURE_WORKFLOW.md
    DAHENG_SDK_NOTES.md

  samples/
    capture_plan_150mm_example.json
    progress_example.json
```

---

## 13. Основные классы

### 13.1 SlotState.cs

```csharp
namespace CassetteDatasetCapture.Model;

public enum SlotState
{
    Empty = 0,
    OccupiedOk = 1,
    CrossSlot = 2,
    ShiftedInSlot = 3,
    DoubleLoadedSuspect = 4,
    Uncertain = 5
}
```

### 13.2 CassetteAnomaly.cs

```csharp
namespace CassetteDatasetCapture.Model;

public sealed class CassetteAnomaly
{
    public string Type { get; set; } = "";
    public int[] Slots { get; set; } = Array.Empty<int>();
    public int Severity { get; set; } = 1;
    public string Note { get; set; } = "";
}
```

### 13.3 CassetteAnnotation.cs

```csharp
namespace CassetteDatasetCapture.Model;

public sealed class CassetteAnnotation
{
    public int CassetteSizeMm { get; set; }
    public int SlotCount { get; set; }
    public SlotState[] SlotStates { get; set; } = Array.Empty<SlotState>();
    public List<CassetteAnomaly> Anomalies { get; set; } = new();

    public string NormalOccupancy =>
        new string(SlotStates.Select(s => s == SlotState.OccupiedOk ? '1' : '0').ToArray());

    public string BlockedSlots =>
        new string(SlotStates.Select(s => s == SlotState.Empty ? '0' : '1').ToArray());

    public string SlotStatesString =>
        new string(SlotStates.Select(s => ((int)s).ToString()[0]).ToArray());
}
```

### 13.4 ICameraService.cs

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

### 13.5 MockCameraService.cs

На первом этапе обязательно реализовать mock-камеру.  
Она нужна, чтобы разработать UI и DatasetWriter без реальной камеры.

```csharp
using System.Drawing;
using System.Drawing.Imaging;

namespace CassetteDatasetCapture.Camera;

public sealed class MockCameraService : ICameraService
{
    public bool IsConnected { get; private set; }
    public bool IsLive { get; private set; }

    public double ExposureUs { get; set; } = 8000;
    public double Gain { get; set; } = 0;

    public void Connect()
    {
        IsConnected = true;
    }

    public void Disconnect()
    {
        IsLive = false;
        IsConnected = false;
    }

    public void StartLive()
    {
        if (!IsConnected)
            Connect();

        IsLive = true;
    }

    public void StopLive()
    {
        IsLive = false;
    }

    public Bitmap GrabFrame()
    {
        var bmp = new Bitmap(1200, 900, PixelFormat.Format24bppRgb);

        using var g = Graphics.FromImage(bmp);
        g.Clear(Color.Black);

        using var pen = new Pen(Color.White, 2);
        using var brush = new SolidBrush(Color.FromArgb(180, 180, 180));

        for (int i = 0; i < 25; i++)
        {
            int y = 60 + i * 30;
            g.DrawLine(pen, 100, y, 1100, y);
        }

        g.FillEllipse(brush, 320, 200, 520, 520);

        return bmp;
    }

    public void Dispose()
    {
        Disconnect();
    }
}
```

### 13.6 DahengCameraService.cs

На MVP-этапе оставить как адаптер с TODO, потому что конкретные имена классов .NET wrapper зависят от установленной версии Daheng Galaxy SDK.

Требования:

- использовать Daheng Galaxy SDK for Windows;
- сначала проверить наличие готовых C#/.NET примеров в SDK;
- если есть .NET wrapper, использовать его;
- если нет .NET wrapper, сделать P/Invoke только на втором этапе;
- не завязывать UI напрямую на Daheng SDK;
- вся работа с камерой только через `ICameraService`.

```csharp
using System.Drawing;

namespace CassetteDatasetCapture.Camera;

public sealed class DahengCameraService : ICameraService
{
    public bool IsConnected { get; private set; }
    public bool IsLive { get; private set; }

    public double ExposureUs { get; set; } = 8000;
    public double Gain { get; set; } = 0;

    public void Connect()
    {
        // TODO:
        // 1. Load Daheng Galaxy SDK device manager
        // 2. Enumerate devices
        // 3. Open first or selected camera
        // 4. Apply ExposureUs and Gain
        // 5. Disable auto exposure/gain if available
        throw new NotImplementedException("Implement using Daheng Galaxy SDK .NET wrapper.");
    }

    public void Disconnect()
    {
        // TODO: stop stream and close device.
        IsLive = false;
        IsConnected = false;
    }

    public void StartLive()
    {
        // TODO: start stream.
        IsLive = true;
    }

    public void StopLive()
    {
        // TODO: stop stream.
        IsLive = false;
    }

    public Bitmap GrabFrame()
    {
        // TODO:
        // 1. Grab one frame from Daheng camera
        // 2. Convert Mono8/Mono12 to Bitmap
        // 3. Return Bitmap
        throw new NotImplementedException("Implement frame grabbing using Daheng Galaxy SDK.");
    }

    public void Dispose()
    {
        Disconnect();
    }
}
```

---

## 14. CapturePlan validation

Нужно валидировать `capture_plan.json` перед запуском.

Проверки:

1. `slot_count > 0`
2. длина `normal_occupancy == slot_count`
3. длина `blocked_slots == slot_count`
4. длина `slot_states == slot_count`
5. все символы в `normal_occupancy` — только `0` или `1`
6. все символы в `blocked_slots` — только `0` или `1`
7. все символы в `slot_states` — `0..5`
8. если `slot_states[i] == 1`, то `normal_occupancy[i] == 1`
9. если `slot_states[i] != 0`, то `blocked_slots[i] == 1`
10. если anomaly type = `cross_slot_plate`, то:
    - slots содержит ровно 2 значения;
    - слоты в диапазоне 1..slot_count;
    - обычно слоты должны быть соседними;
    - оба слота должны иметь `slot_states = 2`;
    - оба слота должны иметь `blocked_slots = 1`;
    - оба слота должны иметь `normal_occupancy = 0`.

---

## 15. Сценарий работы приложения

### 15.1 Первый запуск

1. Пользователь выбирает папку проекта.
2. Программа создаёт структуру:
   - `images/`
   - `labels.csv`
   - `labels.jsonl`
   - `progress.json`, если его нет.
3. Пользователь загружает `capture_plan.json`.
4. Программа валидирует план.
5. Программа показывает первую pending-конфигурацию.

### 15.2 Съёмка

1. Оператор видит текущую конфигурацию.
2. Оператор собирает кассету физически.
3. Оператор нажимает Capture.
4. Программа делает снимок.
5. Программа сохраняет PNG.
6. Программа пишет запись в CSV и JSONL.
7. Программа увеличивает `shots_done`.
8. Если `shots_done >= shots_per_config`, конфигурация становится `done`.
9. Программа переходит к следующей pending-конфигурации.

### 15.3 Retake

Retake должен:

- либо удалить последний снимок и последнюю запись из временного индекса;
- либо проще: пометить последнюю запись как `rejected`, а новый снимок сохранить как следующий.

Для MVP выбрать второй вариант: не удалять файлы, а помечать статусом `rejected`.

### 15.4 Skip

Skip помечает текущую конфигурацию как `skipped` и переходит к следующей.

### 15.5 Needs Review

Оператор может пометить снимок или конфигурацию как `needs_review`.

---

## 16. Генерация capture_plan.json

В MVP можно вручную подготовить `capture_plan.json`.

Позже можно добавить отдельный генератор планов.

Минимальный набор конфигураций:

```text
1. empty
2. full
3. single_slot_01 ... single_slot_N
4. adjacent_pair_01_02 ... adjacent_pair_N-1_N
5. groups of 3–5 plates
6. random fill 10%
7. random fill 25%
8. random fill 50%
9. random fill 75%
10. random fill 90%
11. nearly full with one empty slot
12. cross_slot_01_02 ... cross_slot_N-1_N
13. cross_slot surrounded by normal plates
14. edge slot cases
15. uncertain / borderline cases
```

Рекомендуемый баланс:

```text
70–80% нормальные конфигурации
5–10% cross-slot
5–10% другие дефекты посадки
5% плохие/пограничные изображения
```

---

## 17. Требования к сохранению изображений

Для каждого capture:

1. Сформировать путь:

```text
images/{cassette_size_mm}mm/{config_id}/{config_id}_{timestamp}_{shot_index}.png
```

2. Сохранить Bitmap в PNG.
3. Записать относительный путь в labels.csv/jsonl.
4. Использовать атомарную запись или безопасную последовательность:
   - сначала сохранить изображение;
   - затем записать label;
   - затем обновить progress.json.

---

## 18. Coding guidelines для Codex

### 18.1 Общие правила

- Не писать всю логику в MainForm.
- UI не должен знать деталей Daheng SDK.
- Камера доступна только через `ICameraService`.
- Разметка должна быть отдельной от UI.
- Файловая запись должна быть в `DatasetWriter`.
- Валидация плана должна быть в `CapturePlanValidator`.
- Прогресс должен сохраняться после каждого снимка.
- Не использовать магические строки для статусов, лучше enum.
- Использовать nullable reference types.
- Включить `ImplicitUsings`.
- Код должен быть максимально простым и поддерживаемым.

### 18.2 Стиль

- Namespace: `CassetteDatasetCapture.*`
- Один public class на файл.
- Использовать `sealed` для классов, если наследование не нужно.
- Исключения должны иметь понятные сообщения.
- Все пути к файлам должны работать с Unicode.
- CSV должен корректно экранировать кавычки и запятые.
- JSON писать через `System.Text.Json`.

### 18.3 Тесты

Добавить unit-тесты минимум для:

- `CassetteAnnotation.NormalOccupancy`
- `CassetteAnnotation.BlockedSlots`
- `CassetteAnnotation.SlotStatesString`
- `CapturePlanValidator`
- cross-slot validation
- `DatasetWriter` CSV escaping
- `ProgressStore` load/save

---

## 19. MVP scope

Codex должен сначала реализовать MVP без реальной камеры.

### MVP включает

- .NET 8 WinForms проект;
- `MockCameraService`;
- загрузка `capture_plan.json`;
- валидация плана;
- отображение текущей конфигурации;
- отображение карты слотов;
- Capture с mock-кадром;
- сохранение PNG;
- сохранение labels.csv;
- сохранение labels.jsonl;
- progress.json;
- кнопки Next / Previous / Skip;
- basic error handling.

### MVP НЕ включает

- реальную Daheng-интеграцию;
- автоматическое распознавание изображения;
- сложную калибровку;
- редактирование capture_plan.json из UI;
- обучение модели;
- многокамерный режим.

---

## 20. Phase 2 scope

После MVP:

1. Добавить `DahengCameraService`.
2. Добавить выбор камеры из списка.
3. Добавить live-view с реальной камеры.
4. Добавить настройку Exposure/Gain из UI.
5. Добавить сохранение camera metadata.
6. Добавить режим проверки последнего снимка.
7. Добавить генератор `capture_plan.json`.
8. Добавить экспорт в COCO/YOLO/Parquet при необходимости.

---

## 21. Acceptance criteria

MVP считается готовым, если:

1. Приложение запускается на Windows.
2. Можно выбрать папку проекта.
3. Можно загрузить валидный `capture_plan.json`.
4. Невалидный план показывает понятную ошибку.
5. Приложение показывает текущую конфигурацию.
6. Визуальная карта слотов соответствует `slot_states`.
7. Capture создаёт PNG-файл.
8. Capture добавляет строку в `labels.csv`.
9. Capture добавляет JSON-строку в `labels.jsonl`.
10. `progress.json` обновляется после каждого снимка.
11. После перезапуска приложение продолжает с нужной конфигурации.
12. Cross-slot case корректно сохраняется:
    - `normal_occupancy` = 0 на затронутых слотах;
    - `blocked_slots` = 1 на затронутых слотах;
    - `slot_states` = 2 на затронутых слотах;
    - `anomalies_json` содержит `cross_slot_plate`.

---

## 22. Пример минимального capture_plan.json для тестов

```json
{
  "project": "cassette_150mm_dataset_test",
  "cassette_size_mm": 150,
  "slot_count": 25,
  "shots_per_config": 2,
  "default_exposure_us": 8000,
  "default_gain": 0,
  "configs": [
    {
      "id": "cfg_000001",
      "name": "empty",
      "normal_occupancy": "0000000000000000000000000",
      "blocked_slots": "0000000000000000000000000",
      "slot_states": "0000000000000000000000000",
      "anomalies": [],
      "operator_instruction": "Оставить кассету пустой"
    },
    {
      "id": "cfg_000002",
      "name": "single_slot_01",
      "normal_occupancy": "1000000000000000000000000",
      "blocked_slots": "1000000000000000000000000",
      "slot_states": "1000000000000000000000000",
      "anomalies": [],
      "operator_instruction": "Поставить пластину в слот 1"
    },
    {
      "id": "cfg_000003",
      "name": "cross_slot_08_09",
      "normal_occupancy": "0000000000000000000000000",
      "blocked_slots": "0000000110000000000000000",
      "slot_states": "0000000220000000000000000",
      "anomalies": [
        {
          "type": "cross_slot_plate",
          "slots": [8, 9],
          "severity": 2,
          "note": "Одна пластина между слотами 8 и 9"
        }
      ],
      "operator_instruction": "Установить одну пластину перекошенно: одна сторона в слот 8, другая сторона в слот 9"
    }
  ]
}
```

---

## 23. Важное замечание по индексации слотов

Для оператора слоты отображаются с 1:

```text
1, 2, 3, ..., N
```

Внутри массивов C# индексация с 0.

Правило:

```text
operator_slot_number = array_index + 1
```

В `anomalies.slots` использовать операторскую индексацию, то есть 1-based.

---

## 24. Важное замечание по ML-назначению полей

Для обучения могут использоваться разные target-поля:

### Простая задача

```text
image -> normal_occupancy
```

Модель определяет только правильно установленные пластины.

### Практическая задача

```text
image -> blocked_slots
```

Модель определяет, какие слоты физически заняты или заблокированы.

### Расширенная задача

```text
image -> slot_states
```

Модель классифицирует состояние каждого слота.

### Аномалии

```text
image -> anomalies
```

Можно использовать отдельно для анализа дефектов или как дополнительный head модели.

---

## 25. Итоговая инструкция для Codex

Реализуй C#/.NET 8 WinForms приложение `CassetteDatasetCapture` по этому техническому заданию.

Начни с MVP без реальной камеры:

1. Создай структуру проекта.
2. Реализуй модели.
3. Реализуй загрузку и валидацию `capture_plan.json`.
4. Реализуй `progress.json`.
5. Реализуй `MockCameraService`.
6. Реализуй `DatasetWriter`.
7. Реализуй WinForms UI.
8. Добавь тестовый `capture_plan_150mm_example.json`.
9. Добавь unit-тесты для ключевой логики.

Не реализуй Daheng SDK сразу.  
Оставь `DahengCameraService` как TODO-адаптер через `ICameraService`.

Код должен быть готов к тому, чтобы на Phase 2 заменить `MockCameraService` на реальную Daheng-камеру без переписывания UI и логики датасета.
