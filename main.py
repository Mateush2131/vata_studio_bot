# main.py - рабочая версия без проблемных импортов
import asyncio
import logging
import sys
import csv
import aiohttp
from io import StringIO
from datetime import datetime
from typing import Dict, List, Optional, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# ========== КЛАСС ДЛЯ GOOGLE SHEETS ==========
class GoogleSheetsClient:
    """Клиент для работы с Google Sheets"""
    
    def __init__(self, sheets_config: dict, cache_settings: dict):
        self.config = sheets_config
        self.cache_settings = cache_settings
        self.cache = {}
        self.cache_time = {}
        self.session = None
    
    async def init_session(self):
        """Инициализация HTTP сессии"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Закрытие HTTP сессии"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def fetch_sheet(self, sheet_id: str, sheet_name: str = "") -> List[Dict]:
        """Загрузка таблицы"""
        try:
            await self.init_session()
            
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            logger.info(f"📥 Загружаю {sheet_name}")
            
            async with self.session.get(url, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"❌ Ошибка {response.status} для {sheet_name}")
                    return []
                
                content = await response.text(encoding='utf-8')
                
                if not content or len(content) < 10:
                    logger.warning(f"⚠️ Таблица {sheet_name} пустая")
                    return []
                
                # Парсинг CSV
                data = []
                try:
                    reader = csv.DictReader(StringIO(content))
                    for row in reader:
                        data.append(row)
                except Exception as e:
                    logger.error(f"❌ Ошибка парсинга CSV {sheet_name}: {e}")
                    # Попробуем простой парсинг
                    lines = content.strip().split('\n')
                    if len(lines) > 1:
                        headers = lines[0].split(',')
                        for line in lines[1:]:
                            values = line.split(',')
                            row = {}
                            for i, header in enumerate(headers):
                                if i < len(values):
                                    row[header.strip()] = values[i].strip()
                                else:
                                    row[header.strip()] = ""
                            data.append(row)
                
                logger.info(f"✅ {sheet_name}: {len(data)} записей")
                
                # Сохраняем в кэш
                self.cache[sheet_name] = data
                self.cache_time[sheet_name] = datetime.now()
                
                return data
                
        except asyncio.TimeoutError:
            logger.error(f"⏱️ Таймаут загрузки {sheet_name}")
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки {sheet_name}: {e}")
            return []
    
    async def load_all_data(self) -> Dict[str, Any]:
        """Загружает все таблицы"""
        tasks = {}
        
        for sheet_type, sheet_id in self.config.items():
            tasks[sheet_type] = asyncio.create_task(
                self.fetch_sheet(sheet_id, sheet_type)
            )
        
        results = {}
        for sheet_type, task in tasks.items():
            try:
                data = await task
                results[sheet_type] = data
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки {sheet_type}: {e}")
                results[sheet_type] = []
        
        # Обрабатываем синонимы
        if "synonyms" in results:
            synonyms_dict = {}
            for row in results["synonyms"]:
                for key, value in row.items():
                    if value and ('синон' in key.lower() or 'слово' in key.lower()):
                        words = [word.strip().lower() for word in value.split(',') if word.strip()]
                        if words:
                            main_word = words[0]
                            synonyms_dict[main_word] = words[1:] if len(words) > 1 else []
            
            results["synonyms_dict"] = synonyms_dict
            logger.info(f"📝 Синонимов: {len(synonyms_dict)} групп")
        
        return results

# ========== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ==========
gsheets_client = None
data_loaded = False

async def load_google_sheets_data():
    """Загружает данные из Google Sheets"""
    global gsheets_client, data_loaded
    
    try:
        # Настройки
        SHEETS_CONFIG = {
            "tariffs": "1QdYcS49m0azcHssHwih3BN6UCUhfgdwAJZs6no4Wgfs",
            "models": "1Bcm2vhghVGmqIiARayxiQ5bPMoFFqt_2Rd2ockUw3BE",
            "synonyms": "1zXXjjFY6-TIuBW87WpEHAPzKm-VQveKM1l4dSOLjL-I",
        }
        
        CACHE_SETTINGS = {
            "tariffs": 300,
            "models": 300,
            "synonyms": 600,
        }
        
        # Инициализация клиента
        gsheets_client = GoogleSheetsClient(SHEETS_CONFIG, CACHE_SETTINGS)
        
        # Загрузка данных
        logger.info("📥 Загружаю данные из Google Sheets...")
        data = await gsheets_client.load_all_data()
        
        if data:
            tariffs_count = len(data.get("tariffs", []))
            models_count = len(data.get("models", []))
            synonyms_count = len(data.get("synonyms_dict", {}))
            
            logger.info(f"✅ Данные загружены: {tariffs_count} тарифов, {models_count} моделей, {synonyms_count} групп синонимов")
            data_loaded = True
            return True
        else:
            logger.error("❌ Не удалось загрузить данные")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки данных: {e}")
        return False

# ========== ОСНОВНОЙ КОД БОТА ==========
async def main():
    """Основная функция запуска бота"""
    global gsheets_client, data_loaded
    
    try:
        from aiogram import Bot, Dispatcher
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        from aiogram.filters import CommandStart, Command
        from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
        from aiogram import F
        
        # Токен бота
        BOT_TOKEN = "8090282078:AAHG5d3aHaPumUJWo87V1moLw2JNArX_Uok"
        
        # Инициализация бота
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # Инициализация диспетчера
        dp = Dispatcher()
        
        # Загружаем данные при старте
        await load_google_sheets_data()
        
        # ========== КЛАВИАТУРЫ ==========
        def get_main_keyboard():
            """Основная клавиатура"""
            keyboard = [
                [
                    InlineKeyboardButton(text="📋 Тарифы", callback_data="menu_tariffs"),
                    InlineKeyboardButton(text="👥 Модели", callback_data="menu_models"),
                ],
                [
                    InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help"),
                    InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_reload"),
                ]
            ]
            return InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        def get_tariffs_keyboard():
            """Клавиатура для тарифов"""
            keyboard = [
                [
                    InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main"),
                    InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_reload"),
                ]
            ]
            return InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        def get_models_keyboard():
            """Клавиатура для моделей"""
            keyboard = [
                [
                    InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main"),
                    InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_reload"),
                ]
            ]
            return InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # ========== ОСНОВНЫЕ КОМАНДЫ ==========
        @dp.message(CommandStart())
        async def cmd_start(message: Message):
            welcome_text = """
👋 <b>Добро пожаловать в Vata Studio Assistant!</b>

Я ваш умный помощник по фото- и видеосъемке для маркетплейсов.

<b>Что я умею:</b>
• 📋 Рассказывать о тарифах и услугах
• 👥 Показывать информацию о моделях
• 🤖 Отвечать на вопросы на естественном языке

<b>Статус данных:</b> {status}
            """
            
            status = "✅ Загружены" if data_loaded else "❌ Не загружены (используйте /reload)"
            
            await message.answer(
                welcome_text.format(status=status),
                reply_markup=get_main_keyboard()
            )
        
        @dp.message(Command("help"))
        async def cmd_help(message: Message):
            help_text = """
📋 <b>Доступные команды:</b>

/start - Начать диалог
/help - Эта справка
/tariffs - Все тарифы
/models - Все модели
/reload - Обновить данные
/debug - Техническая информация

💬 <b>Примеры вопросов:</b>
• "тарифы" или "услуги"
• "базовый пакет" или "vata prod"
• "модели для мобильной съемки"
• "когда свободна Хлоя?"
            """
            await message.answer(help_text)
        
        @dp.message(Command("tariffs"))
        async def cmd_tariffs(message: Message):
            if not data_loaded or not gsheets_client:
                await message.answer("❌ Данные не загружены. Используйте /reload")
                return
            
            tariffs = gsheets_client.cache.get("tariffs", [])
            
            if not tariffs:
                await message.answer("⚠️ Тарифы не найдены в таблице")
                return
            
            response = ["<b>📋 Наши тарифы:</b>\n"]
            
            for i, tariff in enumerate(tariffs[:10], 1):
                name = tariff.get("Название тарифа", tariff.get("Тариф", f"Тариф {i}"))
                price = tariff.get("Цена за 1 арт, руб.", tariff.get("Цена", "?"))
                frames = tariff.get("Количество кадров", tariff.get("Кадры", "?"))
                
                response.append(f"{i}. <b>{name}</b>")
                response.append(f"   💰 Цена: {price}₽")
                response.append(f"   📸 Кадров: {frames}")
                
                desc = tariff.get("Описание", "")
                if desc:
                    short_desc = desc[:50] + "..." if len(desc) > 50 else desc
                    response.append(f"   📝 {short_desc}")
                
                response.append("")
            
            if len(tariffs) > 10:
                response.append(f"<i>И еще {len(tariffs) - 10} тарифов...</i>")
            
            response.append("\n<i>Напишите название тарифа для подробностей</i>")
            
            await message.answer(
                "\n".join(response),
                reply_markup=get_tariffs_keyboard()
            )
        
        @dp.message(Command("models"))
        async def cmd_models(message: Message):
            if not data_loaded or not gsheets_client:
                await message.answer("❌ Данные не загружены. Используйте /reload")
                return
            
            models = gsheets_client.cache.get("models", [])
            
            if not models:
                await message.answer("⚠️ Модели не найдены в таблице")
                return
            
            response = ["<b>👥 Наши модели:</b>\n"]
            
            for model in models[:15]:
                name = model.get("Имя", model.get("Модель", "Без имени"))
                height = model.get("Рост", "?")
                shooting_type = model.get("Тип съемок", "")
                
                response.append(f"• <b>{name}</b> - рост {height} см")
                if shooting_type:
                    response.append(f"  🎬 {shooting_type}")
                response.append("")
            
            await message.answer(
                "\n".join(response),
                reply_markup=get_models_keyboard()
            )
        
        @dp.message(Command("reload"))
        async def cmd_reload(message: Message):
            await message.answer("🔄 Загружаю данные из таблиц...")
            
            success = await load_google_sheets_data()
            
            if success:
                tariffs_count = len(gsheets_client.cache.get("tariffs", []))
                models_count = len(gsheets_client.cache.get("models", []))
                
                await message.answer(
                    f"✅ <b>Данные успешно загружены!</b>\n\n"
                    f"📊 Статистика:\n"
                    f"• Тарифов: <b>{tariffs_count}</b>\n"
                    f"• Моделей: <b>{models_count}</b>\n\n"
                    f"Теперь можете использовать команды /tariffs и /models"
                )
            else:
                await message.answer(
                    "❌ <b>Не удалось загрузить данные.</b>\n\n"
                    "Возможные причины:\n"
                    "1. Проблемы с интернет-соединением\n"
                    "2. Таблицы недоступны\n"
                    "3. Ошибка парсинга данных\n\n"
                    "Попробуйте позже."
                )
        
        @dp.message(Command("debug"))
        async def cmd_debug(message: Message):
            debug_text = "<b>🔍 ТЕХНИЧЕСКАЯ ИНФОРМАЦИЯ</b>\n\n"
            
            debug_text += f"• Бот запущен: ✅\n"
            debug_text += f"• Данные загружены: {'✅' if data_loaded else '❌'}\n"
            
            if data_loaded and gsheets_client:
                debug_text += f"• Тарифов: {len(gsheets_client.cache.get('tariffs', []))}\n"
                debug_text += f"• Моделей: {len(gsheets_client.cache.get('models', []))}\n"
                debug_text += f"• Время: {datetime.now().strftime('%H:%M:%S')}\n"
            
            await message.answer(debug_text)
        
        # ========== ОБРАБОТКА КНОПОК ==========
        @dp.callback_query(F.data.startswith("menu_"))
        async def handle_menu_callback(callback: CallbackQuery):
            action = callback.data.split("_")[1]
            
            if action == "tariffs":
                await cmd_tariffs(callback.message)
            elif action == "models":
                await cmd_models(callback.message)
            elif action == "help":
                await cmd_help(callback.message)
            elif action == "reload":
                await cmd_reload(callback.message)
            elif action == "main":
                await cmd_start(callback.message)
            
            await callback.answer()
        
        # ========== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ==========
        @dp.message(F.text)
        async def handle_text(message: Message):
            user_text = message.text.lower().strip()
            
            if not data_loaded:
                await message.answer(
                    "❌ <b>Данные не загружены.</b>\n\n"
                    "Используйте команду <code>/reload</code> для загрузки данных.",
                    reply_markup=get_main_keyboard()
                )
                return
            
            # Поиск тарифов
            if any(keyword in user_text for keyword in ['тариф', 'пакет', 'цена', 'стоит', 'стоимость']):
                tariffs = gsheets_client.cache.get("tariffs", [])
                synonyms = gsheets_client.cache.get("synonyms_dict", {})
                
                # Простой поиск
                found_tariff = None
                for tariff in tariffs:
                    name = tariff.get("Название тарифа", tariff.get("Тариф", "")).lower()
                    if user_text in name or any(word in user_text for word in name.split()):
                        found_tariff = tariff
                        break
                
                if found_tariff:
                    name = found_tariff.get("Название тарифа", found_tariff.get("Тариф", "Без названия"))
                    price = found_tariff.get("Цена за 1 арт, руб.", found_tariff.get("Цена", "?"))
                    frames = found_tariff.get("Количество кадров", found_tariff.get("Кадры", "?"))
                    desc = found_tariff.get("Описание", "")
                    
                    response = [
                        f"<b>🎯 Тариф: {name}</b>",
                        f"💰 <b>Цена:</b> {price}₽ за 1 артикул",
                        f"📸 <b>Кадров:</b> {frames}",
                    ]
                    
                    if desc:
                        response.append(f"📝 <b>Описание:</b> {desc}")
                    
                    await message.answer("\n".join(response))
                else:
                    await cmd_tariffs(message)
            
            # Поиск моделей
            elif any(keyword in user_text for keyword in ['модель', 'девушка', 'рост', 'хлоя', 'яна']):
                models = gsheets_client.cache.get("models", [])
                
                found_model = None
                for model in models:
                    name = model.get("Имя", model.get("Модель", "")).lower()
                    if user_text in name or name in user_text:
                        found_model = model
                        break
                
                if found_model:
                    name = found_model.get("Имя", found_model.get("Модель", "Без имени"))
                    height = found_model.get("Рост", "?")
                    shooting = found_model.get("Тип съемок", "")
                    
                    response = [
                        f"<b>👤 Модель: {name}</b>",
                        f"📏 <b>Рост:</b> {height} см",
                    ]
                    
                    if shooting:
                        response.append(f"🎬 <b>Тип съемок:</b> {shooting}")
                    
                    await message.answer("\n".join(response))
                else:
                    await cmd_models(message)
            
            # Приветствие
            elif any(greet in user_text for greet in ['привет', 'здравств', 'hello', 'hi']):
                await message.answer("👋 Привет! Как я могу помочь?", reply_markup=get_main_keyboard())
            
            # Неизвестный запрос
            else:
                await message.answer(
                    f"🤖 <b>Я не совсем понял ваш запрос.</b>\n\n"
                    f"Вы написали: <i>{message.text}</i>\n\n"
                    f"Попробуйте:\n"
                    f"• Выбрать опцию из меню ниже\n"
                    f"• Использовать команды: /tariffs, /models\n"
                    f"• Написать конкретнее, например 'базовый тариф'",
                    reply_markup=get_main_keyboard()
                )
        
        logger.info("🚀 Бот запускается...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"🚨 Фатальная ошибка: {e}")