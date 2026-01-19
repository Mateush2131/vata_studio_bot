"""
Пакет бота Vata Studio Assistant.

Содержит основные компоненты для обработки сообщений и управления ботом.
"""

__all__ = []

# Автоматический импорт при загрузке пакета
try:
    from .handlers import router
    from .keyboards import get_main_keyboard, get_tariffs_keyboard, get_models_keyboard
    from .states import UserStates
    
    __all__.extend([
        'router',
        'get_main_keyboard',
        'get_tariffs_keyboard', 
        'get_models_keyboard',
        'UserStates'
    ])
    
except ImportError as e:
    print(f"⚠️ Ошибка импорта в bot.__init__: {e}")