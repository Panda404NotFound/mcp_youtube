# MCP YouTube Processor

## Назначение

Инструмент для автоматизации загрузки субтитров с YouTube и создания векторной базы данных для последующего анализа и семантического поиска. Решает две ключевые задачи:

1. Извлечение субтитров из YouTube каналов с помощью YouTube Data API
2. Обработка текстовых файлов и создание векторной базы данных с интеллектуальной группировкой файлов по объему

## Технические возможности

### Модуль загрузки субтитров (`yt_parser.py`)
- Получение списка видео с указанных каналов через YouTube API
- Подсчет общего количества видео на каналах
- Загрузка субтитров на русском и английском языках
- Обнаружение и пропуск уже скачанных субтитров
- Ограничение количества обрабатываемых видео с каждого канала
- Отображение прогресса загрузки с помощью tqdm

### Модуль обработки и векторизации данных (`data.py`)
- Интеллектуальное разбиение текста на чанки по границам предложений
- Автоматическая группировка файлов:
  - Файлы ≥ 1000 слов обрабатываются как отдельные коллекции
  - Файлы < 1000 слов объединяются попарно в одну коллекцию
- Интеграция с ChromaDB для векторизации текста и создания базы данных
- Поддержка демо-режима без зависимости от ChromaDB
- Транслитерация и нормализация имен коллекций

## Системные требования

- Python 3.10+
- Доступ к интернету для загрузки субтитров
- Минимум 2 ГБ оперативной памяти
- Достаточное дисковое пространство для хранения субтитров и векторной базы данных

## Установка на Linux

### 1. Подготовка окружения

```bash
# Установка необходимых системных зависимостей (для Ubuntu/Debian)
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip git

# Клонирование репозитория
git clone https://github.com/Panda404NotFound/mcp_youtube.git
cd mcp_youtube

# Создание виртуального окружения
python3.10 -m venv .venv
source .venv/bin/activate
```

### 2. Установка зависимостей

```bash
# Обновление pip
pip install --upgrade pip

# Установка зависимостей из requirements.txt
pip install -r requirements.txt

# При проблемах с ChromaDB можно установить конкретные версии
pip install chromadb==0.4.18 huggingface_hub==0.16.4 sentence-transformers==2.2.2
```

### 3. Установка и настройка chroma-mcp

```bash
# Установка uv/uvx пакетного менеджера (если не установлен)
curl -L --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/astral-sh/uv/main/install.sh | sh

# Или альтернативно с использованием pip
pip install uv

# Установка chroma-mcp
uv install chroma-mcp
```

Для настройки интеграции с Claude Desktop или другими MCP-совместимыми инструментами, добавьте следующую конфигурацию в файл `claude_desktop_config.json`:

```json
{
  "chroma": {
    "command": "uvx",
    "args": [
      "chroma-mcp",
      "--client-type",
      "persistent",
      "--data-dir",
      "full/path/to/your/chroma_db"
    ]
  }
}
```

Для запуска chroma-mcp вручную с использованием директории проекта:

```bash
uvx chroma-mcp --client-type persistent --data-dir ./chroma_db
```

### 4. Конфигурация

```bash
# Создание файла конфигурации из примера
cp .env.example .env

# Редактирование .env файла для настройки параметров
nano .env
```

Необходимо заполнить в `.env` следующие параметры:
- `YOUTUBE_API_KEY` - API ключ для YouTube Data API
- `CHUNK_SIZE` - размер чанков в словах (по умолчанию 500)
- `MIN_WORDS_THRESHOLD` - порог для объединения файлов (по умолчанию 1000)
- `DATA_FOLDER` - папка для сохранения и обработки файлов (по умолчанию ./data)

## Использование

### Загрузка субтитров

```bash
# Загрузка субтитров со всех указанных в скрипте каналов
python yt_parser.py

# Ограничение количества видео с каждого канала
python yt_parser.py --max 50

# Принудительная повторная загрузка уже скачанных субтитров
python yt_parser.py --force
```

### Обработка текстовых файлов и создание векторной базы данных

```bash
# Обработка всех файлов, группируя маленькие файлы попарно
python data.py --all

# Обработка всех файлов с указанием порога слов
python data.py --all --threshold 500

# Обработка конкретного файла
python data.py --file "имя_файла"

# Запуск в демо-режиме без ChromaDB
python data.py --all --demo
```

## Архитектура проекта

```
mcp_youtube/
├── data.py          # Модуль обработки и векторизации текста
├── yt_parser.py     # Модуль загрузки субтитров с YouTube
├── .env             # Файл конфигурации
├── requirements.txt # Зависимости проекта
├── data/            # Каталог для текстовых файлов и скачанных субтитров
└── chroma_db/       # Каталог для хранения векторной базы данных ChromaDB
```

## Принцип работы

1. `yt_parser.py` загружает субтитры с YouTube и сохраняет их в каталог `youtube/`
2. `data.py` обрабатывает текстовые файлы из каталога `data/` и создает векторную базу данных
3. Большие файлы (≥1000 слов) обрабатываются как отдельные коллекции
4. Маленькие файлы (<1000 слов) группируются попарно для эффективности
5. Результаты сохраняются в векторной базе данных в директории `chroma_db/`

## Устранение неполадок

### Проблемы с ChromaDB

При возникновении ошибок, связанных с ChromaDB, можно:
1. Использовать демо-режим: `python data.py --demo`
2. Установить конкретные версии библиотек:
```bash
pip install chromadb==0.4.18 huggingface_hub==0.16.4 sentence-transformers==2.2.2
```

### Проблемы с chroma-mcp

1. При ошибках запуска chroma-mcp проверьте наличие директории `chroma_db` и права доступа к ней
2. Убедитесь, что uvx установлен и доступен в PATH
3. Для обновления chroma-mcp используйте: `uv install --upgrade chroma-mcp`

### Ошибки YouTube API

1. Убедитесь, что API ключ указан корректно в файле `.env`
2. Проверьте квоту API на панели разработчика Google
3. При превышении квоты используйте параметр `--max` для ограничения количества запросов

## Технические детали

### Алгоритм разбиения на чанки

Текстовые файлы разбиваются на чанки с учетом границ предложений:
1. Предпочтительно завершать чанк на конце предложения
2. Если чанк превышает максимальный размер, он разбивается принудительно
3. Параметр CHUNK_SIZE контролирует максимальный размер чанка в словах

### Векторизация текста

Для векторизации используется:
- Основной метод: Sentence Transformer (`paraphrase-multilingual-MiniLM-L12-v2`)
- Резервный метод: встроенные функции ChromaDB при недоступности Sentence Transformer

### Интеграция с chroma-mcp

Директория `chroma_db/` используется как хранилище для ChromaDB через протокол MCP:
1. Коллекции сохраняются в этой директории в постоянном хранилище
2. Chroma MCP сервер предоставляет доступ к этим коллекциям через стандартизированный интерфейс
3. Для интеграции с внешними инструментами используется конфигурация с указанием на эту директорию
4. Это позволяет AI моделям получать доступ к векторизованным данным для контекстного поиска

