# KMZ Python / Daheng / Modbus TCP

Промышленное приложение контроля кассет по двум камерам Daheng. Геометрия кассеты нормализуется по четырём ArUco `DICT_5X5_100`, после чего слоты проверяются относительно модели, построенной на полностью заполненной кассете.

## Поток обработки

`Camera -> Frame -> InspectionController -> HybridProcessor.process()`

`HybridProcessor` выполняет весь алгоритм:

- поиск ровно четырёх ArUco;
- проверку принадлежности маркеров одному типу;
- соответствие групп `10..13 -> 100 мм`, `20..23 -> 150 мм`, `30..33 -> 200 мм`;
- перспективную нормализацию по внутренним углам реперов;
- применение сохранённого `inspection_roi`;
- построение вертикального Sobel response;
- проверку эталонной кривой каждого слота;
- возврат `OCCUPIED_OK` или `EMPTY` и общего `OK/NG`.

Маркеры могут определяться OpenCV в любом порядке и могут быть повёрнуты: внутренний угол каждого репера выбирается геометрически относительно центра четырёх маркеров.

## Калибровка

Калибровка выполняется на **полностью заполненной кассете**. Она автоматически:

1. нормализует изображение по ArUco;
2. находит ожидаемое количество фронтальных кромок;
3. подбирает `inspection_roi` по области, где кромки стабильно видны;
4. повторно строит кривые внутри найденного ROI;
5. сохраняет эталонную силу каждой кромки;
6. сохраняет ROI и путь к модели отдельно для `camera_id + cassette_type_mm`.

Калибровка с живой камеры:

```bash
python -m app.calibrate --camera cassette_left --cassette 100
```

Калибровка по изображению:

```bash
python -m app.calibrate \
  --camera cassette_left \
  --cassette 100 \
  --image /app/data/calibration_left_100.png
```

Повторить для необходимых сочетаний камер и типов кассет.

Автоматические данные записываются в writable volume `./data`:

```text
data/
  calibration.yaml
  models/
    cassette_left_100.json
    cassette_left_150.json
    cassette_left_200.json
    cassette_right_100.json
    ...
```

`config/config.yaml` остаётся read-only в контейнере. В нём хранятся системные параметры алгоритма, а автоматически подобранный `inspection_roi` хранится в `data/calibration.yaml`.

## Конфигурация обработки

```yaml
processing:
  canonical_size: [1600, 1200]
  calibration_file: /app/data/calibration.yaml
  model_dir: /app/data/models

  aruco_type_groups:
    10: 100
    20: 150
    30: 200

  slot_counts:
    100: 25
    150: 25
    200: 25

  search_radius: 10
  minimum_coverage: 0.55
  minimum_score_ratio: 0.45
  roi_column_coverage: 0.60
```

`minimum_score_ratio` сравнивает текущую силу кромки с эталоном конкретного слота, а `minimum_coverage` требует, чтобы кромка была видна на достаточной доле своей ширины.

## Камеры

- `app/camera/daheng.py` — Daheng Galaxy / `gxipy`;
- `app/camera/mock.py` — тестовый драйвер;
- `app/camera/image_file.py` — кадр из файла;
- `Frame` содержит `image`, `frame_id`, `timestamp_ns`, `camera_id`.

Для реальной камеры замените `driver: mock` на `driver: daheng` и задайте серийный номер.

## Docker

```bash
docker compose up --build
```

`config` монтируется read-only, `data` — с правом записи:

```yaml
volumes:
  - ./config:/app/config:ro
  - ./data:/app/data
```

Проект использует `opencv-contrib-python-headless`, так как модуль `cv2.aruco` входит в contrib-сборку OpenCV.

## Modbus TCP

Holding registers:

- `0` — `COMMAND_ID`;
- `1` — `CAMERA_ID` (`0` левая, `1` правая);
- `2` — `CASSETTE_TYPE` (`100`, `150`, `200`);
- `3` — команда: `1` контроль, `2` ACK, `3` reset error;
- `5` — heartbeat ПЛК.

Input registers:

- `100` — обработанный `COMMAND_ID`;
- `101` — состояние приложения;
- `102` — `OK/NG/ERROR`;
- `103` — код ошибки;
- `104..105` — время обработки, мс;
- `106` — количество слотов;
- `108` — heartbeat приложения;
- `200+` — состояния слотов.

Коды состояний: `0` — `EMPTY`, `1` — `OCCUPIED_OK`, `2` — `CROSS_SLOT`, `3` — `SHIFTED_IN_SLOT`, `4` — `DOUBLE_LOADED_SUSPECT`, `5` — `UNCERTAIN`. Текущий hybrid-алгоритм возвращает только первые два состояния; остальные зарезервированы контрактом датасета.

Если для выбранных `camera_id + cassette_type_mm` нет калибровки, `process()` безопасно возвращает `ERROR`.

## Тесты

```bash
pytest -q
```

Тест калибровки генерирует синтетическую кассету с ArUco 10–13, строит модель, проверяет полностью заполненную кассету и отсутствие одного слота.
