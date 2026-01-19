import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import unicodedata
from urllib.parse import urlparse

def clean_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Очистка текста от лишних символов и нормализация
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина результата
    
    Returns:
        Очищенный текст
    """
    if not text:
        return ""
    
    # Приводим к нормализованной форме Unicode
    text = unicodedata.normalize('NFKC', text)
    
    # Заменяем несколько пробелов на один
    text = re.sub(r'\s+', ' ', text)
    
    # Убираем пробелы в начале и конце
    text = text.strip()
    
    # Убираем лишние переносы строк
    text = re.sub(r'\n+', '\n', text)
    
    # Обрезаем до максимальной длины если нужно
    if max_length and len(text) > max_length:
        text = text[:max_length - 3] + "..."
    
    return text

def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """
    Извлечение ключевых слов из текста
    
    Args:
        text: Исходный текст
        min_length: Минимальная длина слова
    
    Returns:
        Список ключевых слов
    """
    # Русские стоп-слова
    russian_stopwords = {
        'и', 'в', 'на', 'с', 'по', 'для', 'о', 'об', 'от', 'до',
        'за', 'из', 'к', 'у', 'не', 'но', 'а', 'или', 'же', 'бы',
        'то', 'это', 'вот', 'так', 'как', 'уже', 'тоже', 'лишь',
        'он', 'она', 'оно', 'они', 'мы', 'вы', 'я', 'ты', 'его',
        'ее', 'их', 'мой', 'твой', 'наш', 'ваш', 'свой'
    }
    
    # Английские стоп-слова
    english_stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
        'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about',
        'into', 'over', 'after', 'is', 'are', 'was', 'were',
        'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
        'did', 'will', 'would', 'shall', 'should', 'may', 'might',
        'must', 'can', 'could', 'i', 'you', 'he', 'she', 'it',
        'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my',
        'your', 'his', 'its', 'our', 'their', 'mine', 'yours'
    }
    
    # Объединяем стоп-слова
    stopwords = russian_stopwords.union(english_stopwords)
    
    # Извлекаем слова (русские и английские буквы, цифры, дефис)
    words = re.findall(r'[а-яёa-z0-9-]+', text.lower())
    
    # Фильтруем стоп-слова и короткие слова
    keywords = [
        word for word in words 
        if word not in stopwords and len(word) >= min_length
    ]
    
    return keywords

def normalize_query(query: str, synonyms: Dict[str, List[str]]) -> str:
    """
    Нормализация запроса с использованием синонимов
    
    Args:
        query: Исходный запрос
        synonyms: Словарь синонимов
    
    Returns:
        Нормализованный запрос
    """
    if not query or not synonyms:
        return query.lower()
    
    query_lower = query.lower()
    
    # Создаем обратный словарь синонимов для быстрого поиска
    reverse_synonyms = {}
    for main_word, syn_list in synonyms.items():
        for synonym in syn_list:
            reverse_synonyms[synonym] = main_word
    
    # Разбиваем запрос на слова
    words = query_lower.split()
    
    # Заменяем синонимы
    normalized_words = []
    for word in words:
        if word in reverse_synonyms:
            normalized_words.append(reverse_synonyms[word])
        else:
            normalized_words.append(word)
    
    return ' '.join(normalized_words)

def format_tariff_response(tariff: Dict[str, Any]) -> str:
    """
    Форматирование ответа с информацией о тарифе
    
    Args:
        tariff: Данные тарифа
    
    Returns:
        Отформатированный текст
    """
    if not tariff:
        return "❌ Тариф не найден"
    
    # Извлекаем данные с fallback значениями
    name = tariff.get('Название тарифа') or tariff.get('Тариф') or 'Без названия'
    price = tariff.get('Цена за 1 арт, руб.') or tariff.get('Цена') or '?'
    frames = tariff.get('Количество кадров') or tariff.get('Кадры') or '?'
    desc = tariff.get('Описание') or ''
    clients = tariff.get('Для каких клиентов') or ''
    example = tariff.get('Пример ссылки') or ''
    
    # Строим ответ
    lines = [
        f"<b>🎯 Тариф: {name}</b>",
        f"💰 <b>Цена:</b> {price}₽ за 1 артикул",
        f"📸 <b>Кадров:</b> {frames}",
    ]
    
    if desc:
        lines.append(f"📝 <b>Описание:</b> {desc}")
    
    if clients:
        lines.append(f"👥 <b>Для кого:</b> {clients}")
    
    if example and is_valid_url(example):
        lines.append(f"🔗 <b>Пример работ:</b> {example}")
    
    return "\n".join(lines)

def format_model_response(model: Dict[str, Any]) -> str:
    """
    Форматирование ответа с информацией о модели
    
    Args:
        model: Данные модели
    
    Returns:
        Отформатированный текст
    """
    if not model:
        return "❌ Модель не найдена"
    
    # Извлекаем данные с fallback значениями
    name = model.get('Имя') or model.get('Модель') or 'Без имени'
    height = model.get('Рост') or '?'
    params = model.get('Параметры') or ''
    shooting = model.get('Тип съемок') or ''
    portfolio = model.get('Ссылка на портфолио') or model.get('Портфолио') or ''
    dates = model.get('Свободные даты') or ''
    
    # Строим ответ
    lines = [
        f"<b>👤 Модель: {name}</b>",
        f"📏 <b>Рост:</b> {height} см",
    ]
    
    if params:
        lines.append(f"📐 <b>Параметры:</b> {params}")
    
    if shooting:
        lines.append(f"🎬 <b>Тип съемок:</b> {shooting}")
    
    if dates:
        lines.append(f"📅 <b>Свободные даты:</b> {dates}")
    
    if portfolio and is_valid_url(portfolio):
        lines.append(f"🔗 <b>Портфолио:</b> {portfolio}")
    
    return "\n".join(lines)

def is_valid_url(url: str) -> bool:
    """
    Проверка, является ли строка валидным URL
    
    Args:
        url: Строка для проверки
    
    Returns:
        True если валидный URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def safe_json_parse(json_str: str, default: Any = None) -> Any:
    """
    Безопасный парсинг JSON строки
    
    Args:
        json_str: JSON строка
        default: Значение по умолчанию при ошибке
    
    Returns:
        Распаршенный объект или default
    """
    try:
        return json.loads(json_str)
    except:
        return default

def generate_hash(text: str, length: int = 8) -> str:
    """
    Генерация хэша для текста
    
    Args:
        text: Исходный текст
        length: Длина хэша (макс 32)
    
    Returns:
        Хэш строка
    """
    hash_obj = hashlib.md5(text.encode('utf-8'))
    return hash_obj.hexdigest()[:length]

def format_duration(seconds: int) -> str:
    """
    Форматирование длительности в читаемый вид
    
    Args:
        seconds: Количество секунд
    
    Returns:
        Отформатированная строка
    """
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes} мин {seconds} сек"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} час {minutes} мин"

def truncate_text(text: str, max_length: int, ellipsis: str = "...") -> str:
    """
    Обрезка текста с добавлением многоточия
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        ellipsis: Строка для обозначения обрезки
    
    Returns:
        Обрезанный текст
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(ellipsis)] + ellipsis

def parse_date(date_str: str) -> Optional[datetime]:
    """
    Парсинг даты из строки в разных форматах
    
    Args:
        date_str: Строка с датой
    
    Returns:
        Объект datetime или None
    """
    formats = [
        '%d.%m.%Y',      # 01.01.2024
        '%d/%m/%Y',      # 01/01/2024
        '%Y-%m-%d',      # 2024-01-01
        '%d %B %Y',      # 1 января 2024 (нужен locale)
        '%d %b %Y',      # 1 янв 2024
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Пробуем распознать относительные даты
    date_str_lower = date_str.lower()
    
    today = datetime.now()
    
    if date_str_lower == 'сегодня':
        return today
    elif date_str_lower == 'завтра':
        return today + timedelta(days=1)
    elif date_str_lower == 'послезавтра':
        return today + timedelta(days=2)
    
    return None

def validate_phone(phone: str) -> bool:
    """
    Валидация номера телефона
    
    Args:
        phone: Номер телефона
    
    Returns:
        True если номер валидный
    """
    # Убираем все нецифровые символы
    digits = re.sub(r'\D', '', phone)
    
    # Российские номера: начинаются с 7 или 8, длина 11 цифр
    if digits.startswith('7') or digits.startswith('8'):
        return len(digits) == 11
    
    # Международные номера: начинаются с +, длина 10-15 цифр
    if phone.startswith('+'):
        return 10 <= len(digits) <= 15
    
    return False

def format_phone(phone: str) -> str:
    """
    Форматирование номера телефона в стандартный вид
    
    Args:
        phone: Номер телефона
    
    Returns:
        Отформатированный номер
    """
    # Убираем все нецифровые символы
    digits = re.sub(r'\D', '', phone)
    
    if not digits:
        return phone
    
    # Российские номера
    if digits.startswith('7') or digits.startswith('8'):
        if len(digits) == 11:
            return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:]}"
    
    return phone

def split_into_chunks(text: str, max_length: int = 4000) -> List[str]:
    """
    Разделение длинного текста на части для Telegram
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина части
    
    Returns:
        Список частей текста
    """
    if len(text) <= max_length:
        return [text]
    
    # Пытаемся разбить по абзацам
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 1 <= max_length:
            current_chunk += paragraph + '\n'
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = paragraph + '\n'
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def extract_emails(text: str) -> List[str]:
    """
    Извлечение email адресов из текста
    
    Args:
        text: Исходный текст
    
    Returns:
        Список email адресов
    """
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(email_pattern, text)

def calculate_similarity(text1: str, text2: str) -> float:
    """
    Расчет схожести двух текстов (простой алгоритм)
    
    Args:
        text1: Первый текст
        text2: Второй текст
    
    Returns:
        Коэффициент схожести от 0.0 до 1.0
    """
    if not text1 or not text2:
        return 0.0
    
    # Приводим к нижнему регистру
    text1_lower = text1.lower()
    text2_lower = text2.lower()
    
    # Разбиваем на слова
    words1 = set(re.findall(r'[а-яёa-z0-9]+', text1_lower))
    words2 = set(re.findall(r'[а-яёa-z0-9]+', text2_lower))
    
    if not words1 or not words2:
        return 0.0
    
    # Рассчитываем коэффициент Жаккара
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0

class Cache:
    """
    Простой in-memory кэш с TTL
    """
    
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def set(self, key: str, value: Any):
        """Добавление значения в кэш"""
        self.cache[key] = {
            'value': value,
            'expires': datetime.now() + timedelta(seconds=self.ttl)
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Получение значения из кэша"""
        if key not in self.cache:
            return None
        
        item = self.cache[key]
        if datetime.now() > item['expires']:
            del self.cache[key]
            return None
        
        return item['value']
    
    def delete(self, key: str):
        """Удаление значения из кэша"""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        """Очистка всего кэша"""
        self.cache.clear()
    
    def cleanup(self):
        """Очистка просроченных записей"""
        now = datetime.now()
        expired_keys = [
            key for key, item in self.cache.items()
            if now > item['expires']
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)

# Экспорт основных функций и классов
__all__ = [
    'clean_text',
    'extract_keywords',
    'normalize_query',
    'format_tariff_response',
    'format_model_response',
    'is_valid_url',
    'safe_json_parse',
    'generate_hash',
    'format_duration',
    'truncate_text',
    'parse_date',
    'validate_phone',
    'format_phone',
    'split_into_chunks',
    'extract_emails',
    'calculate_similarity',
    'Cache'
]