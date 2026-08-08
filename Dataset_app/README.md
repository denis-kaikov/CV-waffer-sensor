# CassetteDatasetCapture

Windows-приложение для съемки датасета кассет с пластинами.

Оператор собирает кассету по `capture_plan.json`, делает снимок, а программа сохраняет изображение и разметку в `CSV` и `JSONL`.

## Состав репозитория

```text
src/CassetteDatasetCapture/         приложение WinForms
tests/CassetteDatasetCapture.Tests/ автотесты
installer/                          сборка portable-версии и Setup.exe
examples/                           примеры конфигураций
generate_capture_plan.py            генератор capture_plan.json
```

## Требования

- Windows 10/11
- .NET 8 SDK
- Python 3.10+ для генератора конфигураций
- Daheng Galaxy SDK для работы с реальной камерой

Без Galaxy SDK приложение можно запускать в тестовом режиме.

## Запуск

Сборка:

```powershell
dotnet build .\CassetteDatasetCapture.sln --nologo -v:minimal
```

Запуск:

```powershell
dotnet run --project .\src\CassetteDatasetCapture\CassetteDatasetCapture.csproj
```

Порядок работы:

1. Выбрать режим камеры: `Daheng` или тестовый.
2. Указать путь к `capture_plan.json`.
3. Указать каталог датасета.
4. Загрузить план.
5. Снимать кадры по текущей конфигурации.

## Что сохраняется

```text
dataset_root/
  labels.csv
  labels.jsonl
  progress.json
  images/
    150mm/
      cfg_000001/
        cfg_000001_20260710_120001_001.png
```

`progress.json` обновляется после каждого кадра.  
`labels.csv` и `labels.jsonl` содержат итоговую разметку.

## Формат `capture_plan.json`

Верхний уровень:

```json
{
  "project": "cassette_150mm_dataset_v1",
  "cassette_size_mm": 150,
  "slot_count": 25,
  "shots_per_config": 1,
  "default_exposure_us": 8000,
  "default_gain": 0,
  "configs": []
}
```

Одна конфигурация:

```json
{
  "id": "cfg_000001",
  "name": "single_slot_05",
  "normal_occupancy": "0000100000000000000000000",
  "blocked_slots": "0000100000000000000000000",
  "slot_states": "0000100000000000000000000",
  "anomalies": [],
  "operator_instruction": "Установить одну пластину в слот 5."
}
```

Общие правила:

- длина `normal_occupancy`, `blocked_slots` и `slot_states` должна совпадать с `slot_count`
- `normal_occupancy = 1` допустимо только вместе с `slot_states = 1`
- если `slot_states[i] != 0`, то `blocked_slots[i]` должен быть `1`
- номера слотов в `anomalies.slots` идут с `1`

Коды `slot_states`:

- `0` — пусто
- `1` — пластина стоит нормально
- `2` — пластина стоит между соседними слотами
- `3` — пластина перекошена в своем слоте
- `4` — подозрение на двойную загрузку
- `5` — неопределенное состояние

## Конфигурации с перекосом

Перекос внутри одного слота:

```json
{
  "id": "cfg_000002",
  "name": "shifted_in_slot_12",
  "normal_occupancy": "0000000000000000000000000",
  "blocked_slots": "0000000000010000000000000",
  "slot_states": "0000000000030000000000000",
  "anomalies": [
    {
      "type": "shifted_in_slot_plate",
      "slots": [12],
      "severity": 1,
      "note": "Пластина заметно перекошена в своем слоте."
    }
  ],
  "operator_instruction": "Установить пластину в слот 12 с явным перекосом."
}
```

Перекос между двумя соседними слотами:

```json
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
      "note": "Одна пластина занимает два соседних слота."
    }
  ],
  "operator_instruction": "Установить одну пластину между слотами 8 и 9."
}
```

## Генератор конфигураций

Скрипт [generate_capture_plan.py](/C:/CV_daech/generate_capture_plan.py) собирает полный план съемки под один типоразмер.

По умолчанию на один типоразмер формируется:

- `5000` обычных конфигураций
- `1000` конфигураций с перекосом
- `6000` фото при `--shots-per-config 1`

Сценарии обычных фото:

| Сценарий | Количество фото |
| --- | ---: |
| Пустая кассета | 5 |
| Полностью заполненная кассета | 5 |
| Почти полная кассета: 1 пустой слот | 25 |
| Одна пластина в одном слоте | 25 |
| Редкое заполнение, 2–5 пластин | 800 |
| Среднее заполнение, 6–15 пластин | 1300 |
| Плотное заполнение, 16–22 пластины | 450 |
| Группы соседних пластин | 650 |
| Несколько разнесенных групп | 500 |
| Верх / середина / низ кассеты | 250 |
| Чередование через слот | 350 |
| Реалистичные производственные комбинации | 640 |
| **Итого** | **5000** |

Сценарии с перекосом:

| Сценарий | Количество фото |
| --- | ---: |
| Один перекошенный слот, остальные пустые | 25 |
| Почти полная кассета, один перекошенный слот | 25 |
| Перекос при редком заполнении, 2–5 пластин | 200 |
| Перекос при среднем заполнении, 6–15 пластин | 350 |
| Перекос при плотном заполнении, 16–22 пластины | 150 |
| Перекос внутри группы соседних пластин | 150 |
| Несколько разнесенных групп, один перекошенный слот | 75 |
| Два перекошенных слота в одной кассете | 25 |
| **Итого** | **1000** |

Примеры генерации для трех типоразмеров:

```powershell
python .\generate_capture_plan.py --cassette-size-mm 100 --slot-count 25 --shots-per-config 1 --output-path .\capture_plan_100.json
python .\generate_capture_plan.py --cassette-size-mm 150 --slot-count 25 --shots-per-config 1 --output-path .\capture_plan_150.json
python .\generate_capture_plan.py --cassette-size-mm 200 --slot-count 25 --shots-per-config 1 --output-path .\capture_plan_200.json
```

Параметры генератора:

- `--project`
- `--cassette-size-mm`
- `--slot-count`
- `--shots-per-config`
- `--default-exposure-us`
- `--default-gain`
- `--seed`

## Сборка portable и установщика

Сначала нужна Release-сборка:

```powershell
dotnet build .\src\CassetteDatasetCapture\CassetteDatasetCapture.csproj -c Release --no-restore
```

Потом можно собрать portable-версию и `Setup.exe`:

```powershell
powershell -ExecutionPolicy Bypass -File .\installer\build_installer.ps1
```

Результат складывается в `artifacts/`.

## Примечания

- Файлы конфигурации лучше сохранять в `UTF-8`.
- `operator_instruction` остается на русском.
- Минимальный пример лежит в [examples/capture_plan.minimal.json](/C:/CV_daech/examples/capture_plan.minimal.json).
