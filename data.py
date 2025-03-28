import re
import os
import glob
from dotenv import load_dotenv
from transliterate import translit
import argparse
import sys

# Пытаемся импортировать ChromaDB
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except (ImportError, ModuleNotFoundError, Exception) as e:
    print(f"Предупреждение: ChromaDB не доступен: {e}")
    print("Скрипт будет работать в демонстрационном режиме без создания векторной базы данных.")
    CHROMADB_AVAILABLE = False

# Загрузка переменных окружения из .env файла
load_dotenv()

# Получение настроек из .env
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 500))
MIN_WORDS_THRESHOLD = int(os.getenv('MIN_WORDS_THRESHOLD', 1000))  # Минимальный порог количества слов для отдельной коллекции

# Функция для интеллектуального разбиения текста на чанки
def chunk_text(text, chunk_size=CHUNK_SIZE):
    """
    Разбивает текст на чанки, стараясь завершать чанк на конце предложения.
    Если в чанке нет точки, используется обычное разбиение по количеству слов.
    
    Args:
        text (str): Исходный текст
        chunk_size (int): Максимальный размер чанка в словах
        
    Returns:
        list: Список чанков текста
    """
    # Разбиваем текст на слова
    words = re.findall(r'\S+', text)
    chunks = []
    current_chunk = []
    current_word_count = 0
    
    for word in words:
        current_chunk.append(word)
        current_word_count += 1
        
        # Проверяем, заканчивается ли слово на точку, восклицательный или вопросительный знак
        if (word.endswith('.') or word.endswith('!') or word.endswith('?')) and current_word_count >= chunk_size // 1.25:
            # Если это конец предложения и у нас накопилось достаточно слов, завершаем чанк
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_word_count = 0
        elif current_word_count >= chunk_size:
            # Если мы достигли максимального размера чанка без конца предложения,
            # завершаем чанк принудительно
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_word_count = 0
    
    # Добавляем последний чанк, если он не пустой
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

# Функция для подсчета количества слов в тексте
def count_words(text):
    """
    Подсчитывает количество слов в тексте.
    
    Args:
        text (str): Текст для подсчета слов
        
    Returns:
        int: Количество слов в тексте
    """
    words = re.findall(r'\S+', text)
    return len(words)

# Функция для чтения файлов из указанной директории
def read_files_from_directory(directory, supported_formats):
    all_files = []
    for format in supported_formats:
        pattern = os.path.join(directory, f"*.{format}")
        all_files.extend(glob.glob(pattern))
    
    print(f"Найдено {len(all_files)} файлов в папке {directory}")
    return all_files

# Функция для обработки содержимого файла
def process_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Получаем имя файла без пути и расширения
        file_name = os.path.basename(file_path)
        file_name_without_ext = os.path.splitext(file_name)[0]
        
        word_count = count_words(content)
        print(f"Файл '{file_name}' содержит {word_count} слов")
        
        return {
            'content': content,
            'name': file_name,
            'id': file_name_without_ext,
            'word_count': word_count
        }
    except Exception as e:
        print(f"Ошибка при чтении файла {file_path}: {e}")
        return None

# Функция для создания коллекции
def create_collection(name="nutrition_tips"):
    """
    Создает и возвращает коллекцию Chroma DB.
    
    Args:
        name (str): Имя коллекции
        
    Returns:
        Collection: Объект коллекции Chroma DB
    """
    if not CHROMADB_AVAILABLE:
        print(f"Симуляция создания коллекции: '{name}'")
        return MockCollection(name)
    
    try:
        # Инициализация клиента Chroma
        client = chromadb.Client()
        
        # Попытка использовать SentenceTransformer
        try:
            sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="paraphrase-multilingual-MiniLM-L12-v2"
            )
            
            # Создание или получение коллекции с SentenceTransformer
            collection = client.get_or_create_collection(
                name=name,
                embedding_function=sentence_transformer_ef
            )
        except (ImportError, ValueError) as e:
            print(f"Предупреждение: не удалось использовать SentenceTransformer: {e}")
            print("Используем стандартную функцию эмбеддинга.")
            
            # Используем стандартную (встроенную) функцию эмбеддинга
            collection = client.get_or_create_collection(name=name)
            
        return collection
    except Exception as e:
        print(f"Ошибка при создании коллекции: {e}")
        print(f"Использую эмуляцию коллекции для демонстрации.")
        return MockCollection(name)

# Класс-заглушка для эмуляции коллекции ChromaDB
class MockCollection:
    def __init__(self, name):
        self.name = name
        self.documents = []
        self.ids = []
        self.metadatas = []
        print(f"Создана эмуляция коллекции '{name}' для демонстрации")
    
    def add(self, documents, ids, metadatas):
        self.documents.extend(documents)
        self.ids.extend(ids)
        self.metadatas.extend(metadatas)
        print(f"Добавлено {len(documents)} чанков в эмуляцию базы данных")
        
    def query(self, query_texts, n_results=3):
        print(f"Симуляция запроса: {query_texts}")
        if self.documents:
            return {
                "documents": [self.documents[:n_results]],
                "metadatas": [self.metadatas[:n_results]],
                "ids": [self.ids[:n_results]],
                "distances": [[0.1] * min(n_results, len(self.documents))]
            }
        return {"documents": [[]], "metadatas": [[]], "ids": [[]], "distances": [[]]}

# Функция для нормализации имени коллекции
def normalize_collection_name(name, max_length=63):
    """
    Нормализует имя коллекции для базы данных.
    1. Транслитерирует русские символы в латиницу (ужин -> uzhin)
    2. Заменяет пробелы на подчеркивания
    3. Удаляет специальные символы
    4. Обрабатывает случаи, когда имя начинается с цифры
    5. Ограничивает длину имени
    
    Args:
        name (str): Исходное имя коллекции
        max_length (int): Максимальная длина имени (по умолчанию 63 символа)
        
    Returns:
        str: Нормализованное имя, подходящее для базы данных
    """
    # Транслитерация русских символов (ужин -> uzhin)
    name = translit(name, 'ru', reversed=True)
    
    # Заменяем пробелы на подчеркивания (hello world -> hello_world)
    name = re.sub(r'\s+', '_', name)
    
    # Оставляем только допустимые символы: буквы, цифры и подчеркивания
    name = re.sub(r'[^\w\d_]', '', name)
    
    # Если имя начинается с цифры, добавляем префикс
    if re.match(r'^\d', name):
        name = f"coll_{name}"
    
    # Ограничиваем длину имени
    if len(name) > max_length:
        # Если имя слишком длинное, берем начало и хэш
        import hashlib
        hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
        name = name[:max_length-9] + "_" + hash_suffix  # 9 = 8 символов хэша + 1 подчеркивание
    
    # Если имя пустое, используем стандартное
    if not name:
        name = "documents_collection"
    
    return name

# Функция для обработки одного файла и создания векторной базы данных
def process_file_to_collection(file_data, collection_name=None):
    """
    Обрабатывает один файл и создает для него отдельную коллекцию.
    
    Args:
        file_data (dict): Данные файла (id, name, content)
        collection_name (str, optional): Имя коллекции. Если None, используется имя файла.
        
    Returns:
        tuple: (collection, documents, ids, metadatas)
    """
    if collection_name is None:
        collection_name = file_data['id']
        print(f"Используем имя файла в качестве имени коллекции: {collection_name}")
    
    # Нормализация имени коллекции
    original_name = collection_name
    collection_name = normalize_collection_name(collection_name)
    
    if original_name != collection_name:
        print(f"Имя коллекции нормализовано: '{original_name}' -> '{collection_name}'")
    
    # Получаем коллекцию
    print(f"Создание коллекции с именем: '{collection_name}'")
    collection = create_collection(collection_name)
    print(f"Коллекция успешно создана: {collection_name}")
    
    # Подготовка и добавление документов в Chroma DB
    documents = []
    ids = []
    metadatas = []
    chunk_counter = 0
    
    chunks = chunk_text(file_data['content'])
    print(f"Файл '{file_data['name']}' разбит на {len(chunks)} чанков")
    
    for i, chunk in enumerate(chunks):
        documents.append(chunk)
        chunk_id = f"chunk_{chunk_counter}"
        ids.append(chunk_id)
        metadatas.append({
            "source": file_data['name'],
            "chunk_id": chunk_counter,
            "file_id": file_data['id'],
            "chunk_index": i,
            "collection_name": collection_name  # Добавляем имя коллекции в метаданные
        })
        chunk_counter += 1
    
    if documents:
        collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )
        
        print(f"Добавлено {len(documents)} чанков в векторную базу данных")
    else:
        print("Нет чанков для добавления в коллекцию")
    
    return collection, documents, ids, metadatas

# Функция для объединения нескольких файлов в одну коллекцию
def process_files_to_one_collection(files_data, collection_name="combined_small_files"):
    """
    Обрабатывает несколько файлов и создает для них общую коллекцию.
    
    Args:
        files_data (list): Список данных файлов (каждый элемент содержит id, name, content)
        collection_name (str): Имя коллекции
        
    Returns:
        tuple: (collection, documents, ids, metadatas)
    """
    # Нормализация имени коллекции
    original_name = collection_name
    collection_name = normalize_collection_name(collection_name)
    
    if original_name != collection_name:
        print(f"Имя коллекции нормализовано: '{original_name}' -> '{collection_name}'")
    
    # Получаем коллекцию
    print(f"Создание коллекции с именем: '{collection_name}'")
    collection = create_collection(collection_name)
    print(f"Коллекция успешно создана: {collection_name}")
    
    # Подготовка и добавление документов в Chroma DB
    documents = []
    ids = []
    metadatas = []
    chunk_counter = 0
    
    for file_data in files_data:
        chunks = chunk_text(file_data['content'])
        print(f"Файл '{file_data['name']}' разбит на {len(chunks)} чанков")
        
        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            chunk_id = f"chunk_{chunk_counter}"
            ids.append(chunk_id)
            metadatas.append({
                "source": file_data['name'],
                "chunk_id": chunk_counter,
                "file_id": file_data['id'],
                "chunk_index": i,
                "collection_name": collection_name  # Добавляем имя коллекции в метаданные
            })
            chunk_counter += 1
    
    if documents:
        collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )
        
        print(f"Добавлено {len(documents)} чанков в векторную базу данных")
    else:
        print("Нет чанков для добавления в коллекцию")
    
    return collection, documents, ids, metadatas

# Функция для обработки всех файлов
def process_all_files(data_folder, supported_formats):
    """
    Обрабатывает все файлы из указанной папки, создавая отдельные коллекции для файлов с количеством слов >= MIN_WORDS_THRESHOLD
    и объединяя файлы с количеством слов < MIN_WORDS_THRESHOLD в группы по 2 файла.
    
    Args:
        data_folder (str): Путь к папке с данными
        supported_formats (list): Список поддерживаемых форматов файлов
        
    Returns:
        list: Список кортежей (collection, documents, ids, metadatas) для каждой коллекции
    """
    # Создаем папку с данными, если она не существует
    os.makedirs(data_folder, exist_ok=True)
    
    # Чтение и обработка файлов
    all_files = read_files_from_directory(data_folder, supported_formats)
    processed_files = []
    
    for file_path in all_files:
        file_data = process_file(file_path)
        if file_data:
            processed_files.append(file_data)
    
    # Если нет файлов, добавляем пример текста для демонстрации
    if not processed_files:
        print("Файлы не найдены. Добавляем пример текста для демонстрации.")
        
        # Создаем пример файла
        example_text = """Это своего рода «ужин размышлений» и обмен человеческими качествами полезности и интересов."""
        
        example_file_path = os.path.join(data_folder, "example.txt")
        with open(example_file_path, 'w', encoding='utf-8') as f:
            f.write(example_text)
        
        file_data = process_file(example_file_path)
        processed_files.append(file_data)
    
    # Разделяем файлы на большие (>= MIN_WORDS_THRESHOLD слов) и маленькие (< MIN_WORDS_THRESHOLD слов)
    large_files = []
    small_files = []
    
    for file_data in processed_files:
        if file_data['word_count'] >= MIN_WORDS_THRESHOLD:
            large_files.append(file_data)
        else:
            small_files.append(file_data)
    
    print(f"Файлы с >= {MIN_WORDS_THRESHOLD} словами: {len(large_files)}")
    print(f"Файлы с < {MIN_WORDS_THRESHOLD} словами: {len(small_files)}")
    
    results = []
    
    # Обрабатываем большие файлы как отдельные коллекции
    for file_data in large_files:
        print(f"Обработка файла '{file_data['name']}' ({file_data['word_count']} слов) как отдельной коллекции")
        collection_result = process_file_to_collection(file_data)
        results.append(collection_result)
    
    # Объединяем маленькие файлы в группы по 2 файла
    if small_files:
        print(f"Объединение маленьких файлов (менее {MIN_WORDS_THRESHOLD} слов) в группы:")
        # Группируем файлы по два
        for i in range(0, len(small_files), 2):
            if i + 1 < len(small_files):
                # Если есть пара файлов
                file_group = small_files[i:i+2]
                combined_name = f"combined_{file_group[0]['id']}_{file_group[1]['id']}"
                print(f"  Объединение: '{file_group[0]['name']}' и '{file_group[1]['name']}' в коллекцию '{combined_name}'")
                collection_result = process_files_to_one_collection(file_group, combined_name)
                results.append(collection_result)
            else:
                # Если остался один файл без пары
                file_data = small_files[i]
                print(f"  Обработка оставшегося файла '{file_data['name']}' ({file_data['word_count']} слов) как отдельной коллекции")
                collection_result = process_file_to_collection(file_data)
                results.append(collection_result)
    
    print(f"Создано {len(results)} коллекций")
    return results

# Функция для обработки одного файла
def process_one_file(data_folder, supported_formats, target_file=None):
    """
    Обрабатывает один файл из указанной папки и создает для него векторную базу данных.
    
    Args:
        data_folder (str): Путь к папке с данными
        supported_formats (list): Список поддерживаемых форматов файлов
        target_file (str, optional): Имя конкретного файла, который нужно использовать
        
    Returns:
        tuple: (collection, documents, ids, metadatas)
    """
    # Создаем папку с данными, если она не существует
    os.makedirs(data_folder, exist_ok=True)
    
    # Чтение и обработка файлов
    all_files = read_files_from_directory(data_folder, supported_formats)
    processed_files = []
    
    for file_path in all_files:
        file_data = process_file(file_path)
        if file_data:
            processed_files.append(file_data)
    
    # Если нет файлов, добавляем пример текста для демонстрации
    if not processed_files:
        print("Файлы не найдены. Добавляем пример текста для демонстрации.")
        
        # Создаем пример файла
        example_text = """Это своего рода «ужин размышлений» и обмен человеческими качествами полезности и интересов."""
        
        example_file_path = os.path.join(data_folder, "example.txt")
        with open(example_file_path, 'w', encoding='utf-8') as f:
            f.write(example_text)
        
        file_data = process_file(example_file_path)
        processed_files.append(file_data)
    
    # Выбираем файл для обработки
    target_file_data = None
    
    if target_file:
        # Если указан конкретный файл, ищем его в обработанных файлах
        for file_data in processed_files:
            # Проверяем, содержится ли указанный текст в имени файла
            if target_file.lower() in file_data['name'].lower() or target_file.lower() in file_data['id'].lower():
                target_file_data = file_data
                print(f"Найден файл '{file_data['name']}' соответствующий запросу '{target_file}'")
                break
        
        if not target_file_data:
            print(f"Файл, содержащий '{target_file}' не найден, используем первый файл")
            target_file_data = processed_files[0]
    else:
        # Если файл не указан, используем первый файл
        target_file_data = processed_files[0]
        print(f"Используем первый файл: {target_file_data['name']}")
    
    # Обрабатываем выбранный файл
    return process_file_to_collection(target_file_data)

# Главная функция, если файл запускается напрямую
if __name__ == "__main__":
    # Загрузка переменных окружения из .env файла
    load_dotenv()
    
    # Проверка доступности ChromaDB
    if not CHROMADB_AVAILABLE:
        print("ChromaDB не доступен. Скрипт будет работать в демонстрационном режиме.")
    
    # Получение настроек из .env
    DATA_FOLDER = os.getenv('DATA_FOLDER', './data')
    SUPPORTED_FORMATS = os.getenv('SUPPORTED_FORMATS', 'txt').split(',')
    
    # Парсим аргументы командной строки
    parser = argparse.ArgumentParser(description="Обработка файлов и создание векторной базы данных")
    parser.add_argument('--file', type=str, help='Имя файла для обработки')
    parser.add_argument('--all', action='store_true', help='Обработать все файлы с учетом порога слов')
    parser.add_argument('--threshold', type=int, default=MIN_WORDS_THRESHOLD, 
                        help=f'Минимальный порог слов для отдельной коллекции (по умолчанию {MIN_WORDS_THRESHOLD})')
    parser.add_argument('--demo', action='store_true', help='Запустить в демонстрационном режиме без ChromaDB')
    args = parser.parse_args()
    
    # Если указан демо-режим
    if args.demo:
        CHROMADB_AVAILABLE = False
        print("Запуск в демонстрационном режиме без ChromaDB.")
    
    # Обновляем порог слов, если он был указан в аргументах
    if args.threshold:
        MIN_WORDS_THRESHOLD = args.threshold
    
    print(f"Запуск обработки файлов. CHUNK_SIZE={CHUNK_SIZE}")
    print(f"Папка с данными: {DATA_FOLDER}")
    print(f"Поддерживаемые форматы: {SUPPORTED_FORMATS}")
    print(f"Порог слов для отдельной коллекции: {MIN_WORDS_THRESHOLD}")
    
    if args.all:
        print("Обрабатываем все файлы с учетом порога слов")
        # Создаем коллекции с учетом порога слов
        collections_data = process_all_files(DATA_FOLDER, SUPPORTED_FORMATS)
    else:
        # Обрабатываем один файл
        process_one_file(DATA_FOLDER, SUPPORTED_FORMATS, target_file=args.file)