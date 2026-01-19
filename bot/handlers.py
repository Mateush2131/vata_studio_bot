from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import asyncio
import logging

from bot.states import UserStates
from bot.keyboards import get_main_keyboard, get_tariffs_keyboard, get_models_keyboard
from data.gsheets import GoogleSheetsClient
from data.database import ConversationDatabase
from data.ai_assistant import AIAssistant
from managers.notification import ManagerNotifier
from managers.control import BotController
from config import SHEETS_CONFIG, CACHE_SETTINGS
from utils.helpers import format_tariff_response, format_model_response

logger = logging.getLogger(__name__)

# Роутер
router = Router()

# Глобальные объекты (инициализируются в main.py)
gsheets_client = None
db_client = None
ai_assistant = None
manager_notifier = None
bot_controller = None

# ================== ОБРАБОТЧИКИ КОМАНД ==================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    
    # Проверяем, включен ли бот для пользователя
    if bot_controller and not bot_controller.is_bot_enabled_for_user(message.from_user.id):
        await message.answer("⛔ Бот временно отключен для вас. Обратитесь к менеджеру.")
        return
    
    welcome_text = """
👋 <b>Добро пожаловать в Vata Studio Assistant!</b>

Я ваш умный помощник по фото- и видеосъемке для маркетплейсов.

<b>Что я умею:</b>
• 📋 Рассказывать о тарифах и услугах
• 👥 Показывать информацию о моделях
• 🤖 Отвечать на вопросы на естественном языке
• ❓ Помогать с общими вопросами

<b>Выберите опцию ниже или напишите вопрос:</b>
    """
    
    # Запускаем сессию
    if bot_controller:
        bot_controller.enable_bot_for_user(message.from_user.id)
        bot_controller.record_user_message(message.from_user.id)
    
    # Сохраняем в БД
    if db_client:
        db_client.save_message(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            message="/start",
            is_bot=False
        )
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())
    await state.set_state(UserStates.waiting_for_question)

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
<b>📋 Доступные команды:</b>

/start - Начать диалог (меню)
/help - Эта справка
/tariffs - Все тарифы
/models - Все модели
/reload - Обновить данные
/debug - Техническая информация
/stats - Ваша статистика

<b>💬 Примеры вопросов:</b>
• "тарифы" или "услуги"
• "базовый пакет" или "vata prod"
• "модели для мобильной съемки"
• "когда свободна Хлоя?"
• "помоги выбрать тариф"

<b>Я понимаю синонимы:</b>
кадры = ракурсы = снимки
тариф = пакет = услуга
модель = девушка = лицо для съемки
    """
    
    await message.answer(help_text)

@router.message(Command("tariffs"))
async def cmd_tariffs(message: Message):
    """Обработчик команды /tariffs"""
    await show_tariffs(message)

@router.message(Command("models"))
async def cmd_models(message: Message):
    """Обработчик команды /models"""
    await show_models(message)

@router.message(Command("reload"))
async def cmd_reload(message: Message):
    """Обработчик команды /reload"""
    await reload_data(message)

@router.message(Command("debug"))
async def cmd_debug(message: Message):
    """Обработчик команды /debug"""
    await show_debug_info(message)

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Обработчик команды /stats - статистика пользователя"""
    if not db_client or not bot_controller:
        await message.answer("❌ Статистика временно недоступна")
        return
    
    # Статистика из базы данных
    db_stats = db_client.get_user_stats(message.from_user.id)
    
    # Статистика из контроллера
    session_info = bot_controller.get_user_session_info(message.from_user.id)
    
    stats_text = "<b>📊 Ваша статистика:</b>\n\n"
    
    if db_stats:
        stats_text += f"<b>Сообщений:</b>\n"
        stats_text += f"• Всего: {db_stats['total_messages']}\n"
        stats_text += f"• Ваших: {db_stats['user_messages']}\n"
        stats_text += f"• Ответов бота: {db_stats['bot_messages']}\n\n"
        
        if db_stats['first_message']:
            stats_text += f"<b>Первое сообщение:</b>\n{db_stats['first_message']}\n\n"
    
    if session_info:
        stats_text += f"<b>Текущая сессия:</b>\n"
        stats_text += f"• Длительность: {session_info['session_duration_minutes']} мин\n"
        stats_text += f"• Сообщений: {session_info['message_count']}\n"
        stats_text += f"• Ответов ИИ: {session_info['ai_responses']}\n"
    
    await message.answer(stats_text)

@router.message(Command("manager"))
async def cmd_manager(message: Message):
    """Обработчик команды /manager - вызов менеджера"""
    await call_manager(message)

# ================== ОБРАБОТЧИКИ КНОПОК ==================

@router.callback_query(F.data.startswith("menu_"))
async def handle_menu_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатий на кнопки меню"""
    action = callback.data.split("_")[1]
    
    if action == "tariffs":
        await show_tariffs(callback.message)
    elif action == "models":
        await show_models(callback.message)
    elif action == "help":
        await cmd_help(callback.message)
    elif action == "reload":
        await reload_data(callback.message)
    elif action == "debug":
        await show_debug_info(callback.message)
    elif action == "main":
        await cmd_start(callback.message, state)
    
    await callback.answer()

# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================

async def show_tariffs(message: Message):
    """Показать все тарифы"""
    if not gsheets_client or not gsheets_client.cache.get("tariffs"):
        await message.answer("❌ Данные тарифов не загружены. Используйте /reload")
        return
    
    tariffs = gsheets_client.cache.get("tariffs", [])
    
    if not tariffs:
        await message.answer("⚠️ Тарифы не найдены в таблице")
        return
    
    response = ["<b>📋 Наши тарифы:</b>\n"]
    
    for i, tariff in enumerate(tariffs[:10], 1):
        name = tariff.get("Название тарифа", f"Тариф {i}")
        price = tariff.get("Цена за 1 арт, руб.", "?")
        frames = tariff.get("Количество кадров", "?")
        desc = tariff.get("Описание", "")[:50] + "..." if len(tariff.get("Описание", "")) > 50 else tariff.get("Описание", "")
        
        response.append(f"{i}. <b>{name}</b>")
        response.append(f"   💰 Цена: {price}₽")
        response.append(f"   📸 Кадров: {frames}")
        if desc:
            response.append(f"   📝 {desc}")
        response.append("")
    
    if len(tariffs) > 10:
        response.append(f"<i>И еще {len(tariffs) - 10} тарифов...</i>")
    
    response.append("\n<i>Напишите название тарифа для подробностей</i>")
    
    await message.answer("\n".join(response), reply_markup=get_tariffs_keyboard())

async def show_models(message: Message):
    """Показать всех моделей"""
    if not gsheets_client or not gsheets_client.cache.get("models"):
        await message.answer("❌ Данные моделей не загружены. Используйте /reload")
        return
    
    models = gsheets_client.cache.get("models", [])
    
    if not models:
        await message.answer("⚠️ Модели не найдены в таблице")
        return
    
    response = ["<b>👥 Наши модели:</b>\n"]
    
    for model in models[:15]:
        name = model.get("Имя", "Без имени")
        height = model.get("Рост", "?")
        shooting_type = model.get("Тип съемок", "")
        
        response.append(f"• <b>{name}</b> - рост {height} см")
        if shooting_type:
            response.append(f"  🎬 {shooting_type}")
        response.append("")
    
    await message.answer("\n".join(response), reply_markup=get_models_keyboard())

async def reload_data(message: Message):
    """Перезагрузить данные из таблиц"""
    global gsheets_client
    
    await message.answer("🔄 Загружаю данные из таблиц...")
    
    if not gsheets_client:
        gsheets_client = GoogleSheetsClient(SHEETS_CONFIG, CACHE_SETTINGS)
    
    try:
        data = await gsheets_client.load_all_data()
        
        status_text = """
✅ <b>Данные успешно загружены!</b>

📊 <b>Статистика:</b>
"""
        
        for data_type, items in data.items():
            if data_type != "synonyms_dict":
                status_text += f"• {data_type.capitalize()}: <b>{len(items)}</b> записей\n"
        
        if "synonyms_dict" in data:
            status_text += f"• Синонимов: <b>{len(data['synonyms_dict'])}</b> групп\n"
        
        status_text += """
<b>Теперь можете использовать:</b>
<code>/tariffs</code> - список тарифов
<code>/models</code> - список моделей
Или напишите ваш вопрос
        """
        
        await message.answer(status_text)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        await message.answer("""
❌ <b>Не удалось загрузить данные.</b>

<b>Возможные причины:</b>
1. Проблемы с интернет-соединением
2. Таблицы недоступны
3. Ошибка парсинга данных

Попробуйте позже.
        """)

async def show_debug_info(message: Message):
    """Показать техническую информацию"""
    debug_text = "<b>🔍 ТЕХНИЧЕСКАЯ ИНФОРМАЦИЯ</b>\n\n"
    
    # Информация о данных
    if gsheets_client:
        for data_type in ["tariffs", "models", "synonyms"]:
            if data_type in gsheets_client.cache:
                count = len(gsheets_client.cache[data_type])
                debug_text += f"• {data_type.capitalize()}: {count} записей\n"
    
    # Информация о сессии
    if bot_controller:
        session_info = bot_controller.get_user_session_info(message.from_user.id)
        if session_info:
            debug_text += f"\n<b>Ваша сессия:</b>\n"
            debug_text += f"• Сообщений: {session_info['message_count']}\n"
            debug_text += f"• Ответов ИИ: {session_info['ai_responses']}\n"
            debug_text += f"• Таймаутов набора: {session_info['typing_timeouts']}\n"
    
    # Информация о системе
    if ai_assistant:
        debug_text += f"\n<b>ИИ-ассистент:</b>\n"
        debug_text += f"• Режим: {'включен' if ai_assistant.enabled else 'отключен'}\n"
    
    if manager_notifier:
        stats = manager_notifier.get_notification_stats()
        debug_text += f"\n<b>Уведомления:</b>\n"
        debug_text += f"• Всего вызовов: {stats['total_calls']}\n"
        debug_text += f"• Обработано: {stats['handled_calls']}\n"
    
    await message.answer(debug_text[:4000])

async def call_manager(message: Message):
    """Вызов менеджера"""
    user_id = message.from_user.id
    
    # Получаем историю диалога для контекста
    context = []
    if db_client:
        context = db_client.get_conversation_history(user_id, limit=3)
    
    # Получаем последний вопрос пользователя
    last_question = message.text
    if context and len(context) > 0:
        last_question = context[-1]['text'] if not context[-1]['is_bot'] else "Пользователь вызвал менеджера"
    
    # Уведомляем менеджера
    if manager_notifier:
        success = await manager_notifier.notify_manager(
            user_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            question=last_question,
            context=context
        )
        
        if success:
            await message.answer("✅ <b>Менеджер уведомлен!</b>\n\nС вами свяжутся в ближайшее время.")
        else:
            await message.answer("⚠️ <b>Не удалось уведомить менеджера.</b>\n\nПопробуйте позже или напишите напрямую.")
    else:
        await message.answer("📞 <b>Вызов менеджера зарегистрирован.</b>\n\nС вами свяжутся при первой возможности.")

# ================== ОБРАБОТЧИКИ ТЕКСТА ==================

@router.message(F.text)
async def handle_text_message(message: Message, state: FSMContext):
    """Обработка текстовых сообщений"""
    user_text = message.text.strip()
    user_id = message.from_user.id
    
    logger.info(f"👤 {user_id}: {user_text}")
    
    # Проверяем, включен ли бот для пользователя
    if bot_controller and not bot_controller.is_bot_enabled_for_user(user_id):
        await message.answer("⛔ Бот временно отключен для вас. Обратитесь к менеджеру.")
        return
    
    # Проверяем ограничение скорости сообщений
    if bot_controller and not bot_controller.check_message_rate_limit(user_id):
        await message.answer("⚠️ <b>Слишком много сообщений.</b>\n\nПожалуйста, подождите немного.")
        return
    
    # Записываем активность пользователя
    if bot_controller:
        bot_controller.record_user_message(user_id)
        bot_controller.start_typing_timer(user_id)
    
    # Сохраняем сообщение в БД
    if db_client:
        db_client.save_message(
            user_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            message=user_text,
            is_bot=False
        )
    
    # Проверяем загружены ли данные
    if not gsheets_client or not gsheets_client.cache.get("tariffs"):
        await message.answer("""
❌ <b>Данные не загружены.</b>

Используйте команду <code>/reload</code> для загрузки данных из таблиц.
        """, reply_markup=get_main_keyboard())
        return
    
    # Определяем, нужно ли вызывать менеджера
    if manager_notifier and ai_assistant:
        intent = ai_assistant.detect_intent(user_text)
        if ai_assistant.should_call_manager(user_text, intent):
            await call_manager(message)
            return
    
    # Обрабатываем с помощью ИИ-ассистента
    if ai_assistant and ai_assistant.enabled:
        try:
            # Получаем историю для контекста
            history = []
            if db_client:
                history = db_client.get_conversation_history(user_id, limit=AI_SETTINGS["max_context"])
            
            # Обрабатываем запрос через ИИ
            response = await ai_assistant.process_query(user_text, user_id, history)
            
            # Отправляем ответ
            await message.answer(response, reply_markup=get_main_keyboard())
            
            # Записываем ответ бота
            if db_client:
                db_client.save_message(
                    user_id=user_id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    message=response,
                    is_bot=True
                )
            
            # Записываем ответ ИИ в статистику
            if bot_controller:
                bot_controller.record_ai_response(user_id)
                bot_controller.stop_typing_timer(user_id)
            
            return
            
        except Exception as e:
            logger.error(f"❌ Ошибка ИИ-обработки: {e}")
            # Если ИИ не сработал, продолжаем обычную обработку
    
    # ========== СТАНДАРТНАЯ ОБРАБОТКА ==========
    
    # ========== ПОИСК ТАРИФОВ ==========
    tariff_keywords = ["тариф", "пакет", "услуг", "цена", "стоит", "кадр", "ракурс", "стоимость"]
    if any(keyword in user_text.lower() for keyword in tariff_keywords):
        tariffs = gsheets_client.cache.get("tariffs", [])
        synonyms = gsheets_client.cache.get("synonyms_dict", {})
        
        found_tariff = gsheets_client.search_tariff(user_text, tariffs, synonyms)
        
        if found_tariff:
            response = format_tariff_response(found_tariff)
            await message.answer(response)
            
            # Сохраняем ответ бота
            if db_client:
                db_client.save_message(
                    user_id=user_id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    message=response,
                    is_bot=True
                )
            
        else:
            await show_tariffs(message)
        return
    
    # ========== ПОИСК МОДЕЛЕЙ ==========
    model_keywords = ["модель", "девушка", "парень", "рост", "портфолио", "когда свободн"]
    if any(keyword in user_text.lower() for keyword in model_keywords):
        models = gsheets_client.cache.get("models", [])
        found_model = gsheets_client.search_model(user_text, models)
        
        if found_model:
            response = format_model_response(found_model)
            await message.answer(response)
            
            # Сохраняем ответ бота
            if db_client:
                db_client.save_message(
                    user_id=user_id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    message=response,
                    is_bot=True
                )
            
        else:
            await show_models(message)
        return
    
    # Если запрос не распознан
    unknown_response = f"""
🤖 <b>Я не совсем понял ваш запрос.</b>

Ваш запрос: "<i>{user_text}</i>"

<b>Попробуйте:</b>
• Выбрать опцию из меню ниже
• Использовать команды: /tariffs, /models, /help
• Написать конкретнее, например:
  - "Сколько стоит базовый тариф?"
  - "Покажи модели"
  - "Когда свободна Хлоя?"

Или напишите <code>менеджер</code> для связи со специалистом.
    """
    
    await message.answer(unknown_response, reply_markup=get_main_keyboard())
    
    # Проверяем таймаут набора текста
    if bot_controller:
        if bot_controller.check_typing_timeout(user_id):
            logger.info(f"⏰ Таймаут набора текста у user_id={user_id}")
            # Можно уведомить менеджера о долгом наборе
            if manager_notifier:
                await manager_notifier.notify_typing_timeout(
                    user_id=user_id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name
                )