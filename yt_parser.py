import os
import re
from typing import List, Dict, Optional, Set
import googleapiclient.discovery
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from urllib.parse import urlparse, parse_qs, unquote
import dotenv
from tqdm import tqdm
import time
import argparse

# Загружаем переменные окружения из .env файла
dotenv.load_dotenv()

# Получаем API ключ YouTube из переменных окружения или .env файла
API_KEY = os.getenv("YOUTUBE_API_KEY")
if not API_KEY:
    raise ValueError("API ключ YouTube не найден. Убедитесь, что он указан в .env файле как YOUTUBE_API_KEY")

# Получаем настройки ограничения на количество видео
LIMIT_VIDEOS = os.getenv("LIMIT_VIDEOS", "false").lower() == "true"
MAX_VIDEOS_PER_CHANNEL = int(os.getenv("MAX_VIDEOS_PER_CHANNEL", "100")) if LIMIT_VIDEOS else None

# Константа с каналами для парсинга
CHANNELS = [
    "https://www.youtube.com/@KeyOfDragon_Temier.Pajarh",
    "https://www.youtube.com/@ЛегендыоШавкате"
]

def get_channel_id_from_username(api_key: str, username: str) -> Optional[str]:
    """
    Получает ID канала по имени пользователя или handle с помощью YouTube API.
    
    Args:
        api_key: API ключ YouTube
        username: Имя пользователя или handle канала (без символа @)
        
    Returns:
        ID канала или None, если канал не найден
    """
    # Декодируем URL-encoded username
    username = unquote(username)
    
    # Инициализируем YouTube API
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
    
    # Выполняем поиск канала по имени пользователя
    try:
        search_response = youtube.search().list(
            q=username,
            type="channel",
            part="id,snippet",
            maxResults=1
        ).execute()
        
        # Проверяем, найден ли канал
        if search_response.get("items"):
            channel_id = search_response["items"][0]["id"]["channelId"]
            print(f"Найден ID канала для {username}: {channel_id}")
            return channel_id
        else:
            print(f"Канал с именем {username} не найден")
            return None
    except Exception as e:
        print(f"Ошибка при поиске канала {username}: {e}")
        return None

def get_channel_id_from_url(api_key: str, channel_url: str) -> Optional[str]:
    """
    Извлекает ID канала из URL.
    
    Args:
        api_key: API ключ YouTube
        channel_url: URL канала
        
    Returns:
        ID канала или None, если не удалось извлечь
    """
    parsed_url = urlparse(channel_url)
    path = parsed_url.path.strip('/')
    
    # Декодируем URL-encoded символы
    path = unquote(path)
    
    # Проверяем, содержит ли URL уже ID канала
    if path.startswith('channel/'):
        channel_id = path.split('channel/')[1]
        return channel_id
    
    # Если URL содержит имя пользователя или handle (@username)
    if path.startswith('@'):
        username = path[1:]  # Удаляем символ @
        return get_channel_id_from_username(api_key, username)
    elif path.startswith('user/'):
        username = path.split('user/')[1]
        return get_channel_id_from_username(api_key, username)
    else:
        # Если не удалось определить формат URL, пробуем использовать путь как username
        return get_channel_id_from_username(api_key, path)

def count_total_channel_videos(api_key: str, channel_id: str) -> int:
    """
    Подсчитывает общее количество видео на канале.
    
    Args:
        api_key: API ключ YouTube
        channel_id: ID канала
        
    Returns:
        Общее количество видео на канале
    """
    # Инициализируем YouTube API
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
    
    try:
        # Получаем информацию о канале
        channel_response = youtube.channels().list(
            part="statistics",
            id=channel_id
        ).execute()
        
        if not channel_response.get("items"):
            print(f"Канал с ID {channel_id} не найден")
            return 0
        
        # Получаем количество видео
        video_count = int(channel_response["items"][0]["statistics"]["videoCount"])
        return video_count
    except Exception as e:
        print(f"Ошибка при получении количества видео для канала {channel_id}: {e}")
        return 0

def get_videos_from_channel(api_key: str, channel_id: str, max_results: Optional[int] = None) -> List[Dict]:
    """
    Получает список видео с канала с помощью YouTube API.
    
    Args:
        api_key: API ключ YouTube
        channel_id: ID канала
        max_results: Максимальное количество результатов (если None, загружаются все видео)
        
    Returns:
        Список словарей с информацией о видео (id, title)
    """
    # Инициализируем YouTube API
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
    
    videos = []
    next_page_token = None
    
    try:
        # Сначала получаем uploads playlist ID
        channel_response = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()
        
        if not channel_response.get("items"):
            print(f"Канал с ID {channel_id} не найден")
            return []
        
        uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        
        # Загружаем видео из плейлиста загрузок канала
        while True:
            playlist_response = youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=50,  # Максимальное значение для YouTube API
                pageToken=next_page_token
            ).execute()
            
            # Добавляем видео в список
            for item in playlist_response["items"]:
                video_id = item["snippet"]["resourceId"]["videoId"]
                video_title = item["snippet"]["title"]
                videos.append({
                    "id": video_id,
                    "title": video_title
                })
                
                # Если достигли максимального количества и оно задано, останавливаемся
                if max_results is not None and len(videos) >= max_results:
                    return videos
            
            # Проверяем, есть ли еще страницы
            next_page_token = playlist_response.get("nextPageToken")
            if not next_page_token:
                break
                
            # Пауза между запросами к API для соблюдения лимитов
            time.sleep(0.5)
                
        return videos
    except Exception as e:
        print(f"Ошибка при получении видео для канала {channel_id}: {e}")
        return []

def get_already_downloaded_videos(output_dir: str) -> Set[str]:
    """
    Получает список уже скачанных видео на основе названия файлов.
    
    Args:
        output_dir: Директория с сохраненными субтитрами
        
    Returns:
        Множество ID видео, для которых уже скачаны субтитры
    """
    # Если директория не существует, возвращаем пустое множество
    if not os.path.exists(output_dir):
        return set()
    
    downloaded_videos = set()
    
    # Получаем список всех txt файлов в директории
    txt_files = [f for f in os.listdir(output_dir) if f.endswith('.txt')]
    
    print(f"Найдено {len(txt_files)} уже скачанных файлов субтитров")
    
    return set(txt_files)

def is_already_downloaded(video_title: str, downloaded_files: Set[str]) -> bool:
    """
    Проверяет, были ли уже скачаны субтитры для данного видео.
    
    Args:
        video_title: Название видео
        downloaded_files: Множество имен файлов уже скачанных видео
        
    Returns:
        True, если субтитры уже скачаны, иначе False
    """
    # Очищаем название файла от недопустимых символов (как при сохранении)
    safe_title = re.sub(r'[\\/*?:"<>|]', "_", video_title)
    file_name = f"{safe_title}.txt"
    
    return file_name in downloaded_files

def download_transcript(video_id: str, output_dir: str, video_title: str) -> bool:
    """
    Скачивает субтитры для видео и сохраняет их в файл.
    
    Args:
        video_id: ID видео
        output_dir: Директория для сохранения
        video_title: Название видео
        
    Returns:
        True, если субтитры успешно скачаны, иначе False
    """
    try:
        # Получаем субтитры для видео
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru', 'en'])
        
        # Преобразуем список субтитров в единый текст
        full_text = ""
        for entry in transcript:
            full_text += f"{entry['text']} "
        
        # Очищаем название файла от недопустимых символов
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", video_title)
        
        # Формируем путь к файлу
        file_path = os.path.join(output_dir, f"{safe_title}.txt")
        
        # Сохраняем текст в файл
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(full_text)
            
        return True
    except NoTranscriptFound:
        print(f"Для видео {video_id} ({video_title}) не найдены субтитры на указанных языках")
        return False
    except TranscriptsDisabled:
        print(f"Для видео {video_id} ({video_title}) субтитры отключены")
        return False
    except Exception as e:
        print(f"Ошибка при скачивании субтитров для видео {video_id}: {str(e)}")
        return False

def parse_and_download_transcripts(max_videos_per_channel: Optional[int] = None, force_redownload: bool = False):
    """
    Основная функция для парсинга и скачивания субтитров.
    
    Args:
        max_videos_per_channel: Максимальное количество видео для обработки с каждого канала
                                (None для всех видео)
        force_redownload: Если True, повторно скачивает уже скачанные видео
    """
    # Создаем директорию для сохранения субтитров, если она не существует
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    
    # Получаем список уже скачанных видео
    downloaded_files = get_already_downloaded_videos(output_dir)
    
    total_videos = 0
    channel_videos = {}
    channel_totals = {}
    
    # Если max_videos_per_channel не задан через аргумент, используем значение из .env
    if max_videos_per_channel is None and LIMIT_VIDEOS:
        max_videos_per_channel = MAX_VIDEOS_PER_CHANNEL
        print(f"Используется ограничение на количество видео из .env: {max_videos_per_channel} видео на канал")
    
    print("Получение списка видео с каналов...")
    
    # Получаем список всех видео со всех каналов
    for channel_url in CHANNELS:
        print(f"Обработка канала: {channel_url}")
        
        channel_id = get_channel_id_from_url(API_KEY, channel_url)
        if not channel_id:
            print(f"Не удалось получить ID канала для {channel_url}, пропускаем")
            continue
        
        # Получаем общее количество видео на канале
        total_channel_videos = count_total_channel_videos(API_KEY, channel_id)
        channel_totals[channel_url] = total_channel_videos
        
        print(f"Всего на канале {total_channel_videos} видео")
        
        # Загружаем список видео (все или ограниченное количество)
        videos = get_videos_from_channel(API_KEY, channel_id, max_videos_per_channel)
        channel_videos[channel_url] = videos
        total_videos += len(videos)
        
        print(f"Загружено {len(videos)} видео с канала {channel_url}")
        
        # Пауза между запросами к API для соблюдения лимитов
        time.sleep(1)
    
    print(f"Всего найдено видео: {total_videos}")
    
    # Если нет видео, завершаем работу
    if total_videos == 0:
        print("Не найдено видео для обработки. Завершение работы.")
        return
    
    # Счетчики для отслеживания прогресса
    processed_videos = 0
    successful_downloads = 0
    skipped_videos = 0
    
    # Создаем прогресс-бар для наглядности
    with tqdm(total=total_videos, desc="Скачивание субтитров", unit="видео") as pbar:
        # Скачиваем субтитры для каждого видео
        for channel_url, videos in channel_videos.items():
            for video in videos:
                video_id = video["id"]
                video_title = video["title"]
                
                # Проверяем, скачано ли уже это видео
                if not force_redownload and is_already_downloaded(video_title, downloaded_files):
                    processed_videos += 1
                    skipped_videos += 1
                    pbar.update(1)
                    pbar.set_postfix(успешно=f"{successful_downloads}/{processed_videos}", пропущено=skipped_videos)
                    continue
                
                success = download_transcript(video_id, output_dir, video_title)
                processed_videos += 1
                
                if success:
                    successful_downloads += 1
                
                # Обновляем прогресс-бар
                pbar.update(1)
                pbar.set_postfix(успешно=f"{successful_downloads}/{processed_videos}", пропущено=skipped_videos)
                
                # Небольшая пауза чтобы не перегружать API
                time.sleep(0.5)
    
    print(f"\nЗагрузка завершена:")
    print(f"Обработано: {processed_videos} видео")
    print(f"Успешно скачано: {successful_downloads} видео")
    print(f"Пропущено (уже скачано): {skipped_videos} видео")
    
    # Сравниваем количество обработанных видео с общим количеством видео на каналах
    for channel_url, total_count in channel_totals.items():
        channel_videos_processed = len(channel_videos.get(channel_url, []))
        if channel_videos_processed < total_count:
            print(f"Внимание: Для канала {channel_url} обработано только {channel_videos_processed} из {total_count} видео")

if __name__ == "__main__":
    # Парсим аргументы командной строки
    parser = argparse.ArgumentParser(description="Скачивание субтитров с YouTube каналов")
    parser.add_argument("--max", type=int, help="Максимальное количество видео для обработки с каждого канала", default=None)
    parser.add_argument("--force", action="store_true", help="Принудительно скачать субтитры для уже обработанных видео")
    args = parser.parse_args()
    
    # Аргументы командной строки имеют приоритет над настройками в .env
    parse_and_download_transcripts(max_videos_per_channel=args.max, force_redownload=args.force)