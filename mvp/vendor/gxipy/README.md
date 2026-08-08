# gxipy package

Поместите в этот каталог официальный пакет Daheng Galaxy Python SDK (`gxipy`),
совместимый с Python 3.8 и установленной версией Galaxy SDK.

Поддерживаемые Dockerfile форматы:

- `*.whl`
- `*.tar.gz`
- `*.zip`

Нативные библиотеки Galaxy SDK берутся из образа
`lensorai/docker-daheng-sdk:2.4.2503`. Сам образ содержит главным образом
`libgxiapi.so` и GenTL transport layers, поэтому Python binding поставляется
отдельно.

Без пакета `gxipy` контейнер собирается и работает с драйверами `mock` и
`image_file`, но драйвер `daheng` при запуске сообщит ошибку импорта.
