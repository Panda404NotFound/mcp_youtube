import chromadb
from dotenv import load_dotenv
import os
from data import process_files, chunk_text, process_all_files
import os.path
import re
import argparse

# Загрузка переменных окружения из .env файла
load_dotenv()

# Получение настроек из .env
N_RESULTS = int(os.getenv('N_RESULTS', 3))
DATA_FOLDER = os.getenv('DATA_FOLDER', './data')
SUPPORTED_FORMATS = os.getenv('SUPPORTED_FORMATS', 'txt').split(',')

def run_test_queries(collection, collection_name):
    test_queries = [
        "Что такое настоящая политика по Шавкату?",
        "Как отличить настоящую политику от политики чушек?",
        "Что говорит автор о воздействии информации на человека?",
        "Какую роль играет личная сила в жизни человека?",
        "Как избежать когнитивных искажений под влиянием внешних факторов?"
    ]
    
    print("\n=== ТЕСТИРОВАНИЕ ВЕКТОРНОЙ БАЗЫ ДАННЫХ ===")
    print(f"Тестирование коллекции: {collection_name}")
    for query in test_queries:
        print(f"\nЗапрос: {query}")
        # Используем N_RESULTS из настроек
        results = collection.query(
            query_texts=[query],
            n_results=N_RESULTS
        )
        
        if results['documents'] and results['documents'][0]:
            print(f"Найдено {len(results['documents'][0])} релевантных чанка:")
            for i, doc in enumerate(results['documents'][0]):
                source = results['metadatas'][0][i]['source']
                chunk_id = results['metadatas'][0][i]['chunk_id']
                print(f"Источник: {source}, Чанк #{chunk_id}: {doc[:150]}...")
            print("✅ ТЕСТ ПРОЙДЕН")
        else:
            print("❌ ТЕСТ НЕ ПРОЙДЕН: Результаты не найдены")
    
    print("\n=== ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===")

def test_all_collections(collections_data):
    """
    Запускает тесты на всех коллекциях.
    
    Args:
        collections_data: Список кортежей (collection, documents, ids, metadatas)
    """
    print("\n=== ТЕСТИРОВАНИЕ ВСЕХ КОЛЛЕКЦИЙ ===")
    
    for collection_data in collections_data:
        collection = collection_data[0]
        metadatas = collection_data[3]
        
        if len(metadatas) > 0:
            collection_name = metadatas[0].get("collection_name", "documents_collection")
            run_test_queries(collection, collection_name)
            
            # Сохраняем в постоянное хранилище
            create_persistent_storage(collection, collection_data[1], collection_data[2], collection_data[3], collection_name)

def create_persistent_storage(collection, documents, ids, metadatas, collection_name):
    try:
        persistent_client = chromadb.PersistentClient(path="./chroma_db")
        
        # Удаляем коллекцию и создаем новую
        try:
            persistent_client.delete_collection(name=collection_name)
        except:
            pass
            
        persistent_collection = persistent_client.create_collection(
            name=collection_name, 
            embedding_function=collection._embedding_function
        )
        
        # Добавляем чанки в постоянное хранилище
        persistent_collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )
        
        print(f"\nБаза данных сохранена на диск в папку ./chroma_db, коллекция: {collection_name}")
    except Exception as e:
        print(f"\nОшибка при сохранении базы данных: {e}")

if __name__ == "__main__":
    # Импортируем здесь, чтобы не было циклических импортов
    from data import create_collection
    
    # Парсим аргументы командной строки
    parser = argparse.ArgumentParser(description="Тестирование векторной базы данных")
    parser.add_argument('--file', type=str, help='Имя файла для использования в качестве основы для коллекции')
    parser.add_argument('--all', action='store_true', help='Обработать все файлы и создать отдельные коллекции')
    args = parser.parse_args()
    
    print(f"Настройки тестирования: N_RESULTS={N_RESULTS}")
    print(f"Папка с данными: {DATA_FOLDER}")
    print(f"Поддерживаемые форматы: {SUPPORTED_FORMATS}")
    
    if args.all:
        print("Обрабатываем все файлы отдельно")
        # Получаем все коллекции
        collections_data = process_all_files(DATA_FOLDER, SUPPORTED_FORMATS)
        # Тестируем все коллекции
        test_all_collections(collections_data)
    else:
        if args.file:
            print(f"Целевой файл: {args.file}")
        
        # Получаем коллекцию и добавленные документы для одного файла
        collection, documents, ids, metadatas = process_files(DATA_FOLDER, SUPPORTED_FORMATS, target_file=args.file)
        
        # Получаем имя коллекции из метаданных первого чанка
        collection_name = "documents_collection"
        if len(metadatas) > 0:
            collection_name = metadatas[0].get("collection_name", "documents_collection")
        
        # Запускаем тесты
        run_test_queries(collection, collection_name)
        
        # Сохраняем в постоянное хранилище
        create_persistent_storage(collection, documents, ids, metadatas, collection_name) 