"""
Пакет для управления ботом менеджерами.
Содержит инструменты для уведомления менеджеров и контроля состояния бота.
"""

from .notification import ManagerNotifier
from .control import BotController

__all__ = [
    'ManagerNotifier',
    'BotController'
]