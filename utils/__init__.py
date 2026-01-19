"""
Утилиты для бота Vata Studio Assistant.
"""

from .logger import setup_logging, get_logger, BotLogger
from .helpers import (
    clean_text, extract_keywords, normalize_query,
    format_tariff_response, format_model_response,
    is_valid_url, safe_json_parse, generate_hash,
    format_duration, truncate_text, parse_date,
    validate_phone, format_phone, split_into_chunks,
    extract_emails, calculate_similarity, Cache
)

__all__ = [
    # Логирование
    'setup_logging',
    'get_logger',
    'BotLogger',
    
    # Помощники
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