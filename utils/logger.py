import logging
import sys
import os
from datetime import datetime

class ColorFormatter(logging.Formatter):
    """Цветной форматтер для консоли"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[1;31m', # Bold Red
    }
    
    RESET = '\033[0m'
    
    def format(self, record):
        # Добавляем цвет
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        
        # Добавляем время
        record.asctime = self.formatTime(record, self.datefmt)
        
        # Форматируем сообщение
        return f"{record.asctime} | {record.name} | {record.levelname} | {record.getMessage()}"

def setup_logging():
    """Настройка логирования"""
    # Создаем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Удаляем существующие обработчики
    root_logger.handlers.clear()
    
    # Форматтер для консоли
    console_formatter = ColorFormatter(
        fmt='%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Форматтер для файла
    file_formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Файловый обработчик
    try:
        file_handler = logging.FileHandler('bot.log', encoding='utf-8', mode='a')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
    except Exception as e:
        print(f"⚠️ Не удалось создать файловый обработчик логов: {e}")
        file_handler = None
    
    # Добавляем обработчики
    root_logger.addHandler(console_handler)
    if file_handler:
        root_logger.addHandler(file_handler)
    
    # Уменьшаем уровень логирования для некоторых библиотек
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    # Возвращаем логгер приложения
    app_logger = logging.getLogger('vata_bot')
    app_logger.info("📝 Логирование настроено")
    
    return app_logger

def get_logger(name: str) -> logging.Logger:
    """Получение именованного логгера"""
    return logging.getLogger(name)