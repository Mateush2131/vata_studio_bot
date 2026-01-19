from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Основная клавиатура меню"""
    keyboard = [
        [
            InlineKeyboardButton(text="📋 Тарифы", callback_data="menu_tariffs"),
            InlineKeyboardButton(text="👥 Модели", callback_data="menu_models"),
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_reload"),
        ],
        [
            InlineKeyboardButton(text="🔍 Отладка", callback_data="menu_debug"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_tariffs_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для тарифов"""
    keyboard = [
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_reload"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_models_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для моделей"""
    keyboard = [
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_reload"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)