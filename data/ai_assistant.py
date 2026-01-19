import logging
from typing import List, Dict, Any
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class AIAssistant:
    """Простой ИИ-ассистент для обработки естественного языка"""
    
    def __init__(self, gsheets_client=None, db_client=None):
        self.gsheets_client = gsheets_client
        self.db_client = db_client
        self.enabled = True
        
        # Шаблоны для распознавания интентов
        self.intent_patterns = {
            'greeting': [
                r'привет', r'здравствуй', r'добрый', r'hello', r'hi', r'начать',
                r'здравствуйте', r'доброе утро', r'добрый день', r'добрый вечер'
            ],
            'farewell': [
                r'пока', r'до свидан', r'спасибо', r'благодарю', r'goodbye', r'bye',
                r'всего доброго', r'до встречи'
            ],
            'tariff_info': [
                r'тариф', r'пакет', r'услуг', r'цена', r'стоит', r'стоимость',
                r'сколько стоит', r'прайс', r'цены', r'расценки'
            ],
            'model_info': [
                r'модель', r'девушка', r'парень', r'рост', r'параметр', r'тип съемки',
                r'модели', r'актрис', r'актер'
            ],
            'portfolio_request': [
                r'портфолио', r'пример', r'работ', r'фото', r'видео', r'снимк',
                r'каталог', r'галерея', r'примеры работ'
            ],
            'schedule_request': [
                r'расписан', r'график', r'когда', r'дата', r'время', r'свободн',
                r'занят', r'бронь', r'записаться', r'доступен'
            ],
            'contact_request': [
                r'контакт', r'связь', r'телефон', r'номер', r'email', r'почта',
                r'менеджер', r'администратор', r'помощь человека'
            ],
            'thanks': [
                r'спасибо', r'благодарю', r'отлично', r'супер', r'класс', r'замечательно',
                r'хорошо', r'понятно', r'ясно'
            ]
        }
        
        # Шаблоны ответов
        self.response_templates = {
            'greeting': [
                "Привет! 😊 Рад вас видеть! Чем могу помочь?",
                "Здравствуйте! 👋 Я ваш помощник Vata Studio. Какой у вас вопрос?",
                "Приветствую! Я готов помочь с вопросами о съемках и тарифах."
            ],
            'farewell': [
                "Всего доброго! Обращайтесь еще! 👋",
                "До свидания! Буду рад помочь снова!",
                "Спасибо за обращение! Хорошего дня! ✨"
            ],
            'tariff_info': [
                "Сейчас расскажу о наших тарифах...",
                "У нас есть несколько вариантов тарифов. Давайте посмотрим...",
                "Отличный вопрос! Вот информация о тарифах:"
            ],
            'model_info': [
                "Информация о моделях...",
                "Сейчас покажу доступных моделей...",
                "У нас работают профессиональные модели. Вот информация:"
            ],
            'portfolio_request': [
                "К сожалению, система портфолио временно недоступна. Используйте команды /tariffs и /models для получения информации.",
                "Портфолио в разработке. Пока можете посмотреть информацию о тарифах и моделях.",
                "Раздел портфолио скоро будет доступен. А пока могу рассказать о наших услугах."
            ],
            'schedule_request': [
                "Расписание моделей пока недоступно онлайн. Для записи на съемку свяжитесь с менеджером.",
                "Информация о расписании обновляется. Лучше уточнить у менеджера.",
                "Чтобы узнать точное расписание, напишите 'менеджер' для связи со специалистом."
            ],
            'contact_request': [
                "Чтобы связаться с менеджером, напишите 'менеджер' или подождите, я вызову специалиста.",
                "Сейчас вызову менеджера для вас...",
                "Менеджер скоро свяжется с вами. А пока могу ответить на другие вопросы?"
            ],
            'thanks': [
                "Пожалуйста! Рад был помочь! 😊",
                "Всегда готов помочь! Обращайтесь!",
                "Спасибо за обращение! Если есть еще вопросы - пишите!"
            ],
            'unknown': [
                "Извините, я не совсем понял ваш запрос. Можете уточнить?",
                "Пока не могу ответить на этот вопрос. Попробуйте задать его иначе.",
                "Этот вопрос лучше уточнить у менеджера. Написать 'менеджер'?",
                "Я еще учусь понимать такие запросы. Можете использовать команды из меню?"
            ]
        }
        
        logger.info("🤖 ИИ-ассистент инициализирован")
    
    def detect_intent(self, text: str) -> str:
        """Определение намерения пользователя"""
        text_lower = text.lower()
        
        # Проверяем команды
        if text_lower.startswith('/'):
            return 'command'
        
        # Проверяем шаблоны
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    logger.info(f"🎯 Обнаружен интент: {intent}")
                    return intent
        
        # Если не нашли - проверяем ключевые слова для тарифов/моделей
        tariff_words = ['тариф', 'цена', 'стоит', 'пакет', 'услуг', 'vata', 'prod', 'базов']
        model_words = ['модель', 'девушка', 'парень', 'рост', 'хлоя', 'яна', 'валер', 'тори']
        
        if any(word in text_lower for word in tariff_words):
            return 'tariff_info'
        elif any(word in text_lower for word in model_words):
            return 'model_info'
        
        return 'unknown'
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Извлечение сущностей из текста"""
        entities = {
            'tariff_name': None,
            'model_name': None,
            'question_type': None,
            'date': None,
            'time': None
        }
        
        text_lower = text.lower()
        
        # Извлекаем названия тарифов
        tariff_names = ['базовый', 'vata prod', 'vata', 'prod', 'премиум', 'стандарт']
        for name in tariff_names:
            if name in text_lower:
                entities['tariff_name'] = name
                entities['question_type'] = 'tariff'
                break
        
        # Извлекаем имена моделей
        model_names = ['хлоя', 'яна', 'валерия', 'тори', 'модель']
        for name in model_names:
            if name in text_lower:
                entities['model_name'] = name
                entities['question_type'] = 'model'
                break
        
        # Ищем упоминания о дате/времени
        date_patterns = [
            r'(\d{1,2}[./]\d{1,2}[./]\d{2,4})',  # DD.MM.YYYY
            r'(\d{1,2}\s+[а-я]+)',  # "15 декабря"
            r'(завтра|послезавтра|сегодня)',
            r'(понедельник|вторник|сред[ау]|четверг|пятниц[ау]|суббот[ау]|воскресень[ея])'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text_lower)
            if match:
                entities['date'] = match.group(1)
                break
        
        # Ищем время
        time_pattern = r'(\d{1,2}[:.]\d{2})'
        match = re.search(time_pattern, text_lower)
        if match:
            entities['time'] = match.group(1)
        
        return entities
    
    async def process_query(self, query: str, user_id: int = None, context: List[Dict] = None) -> str:
        """Обработка запроса пользователя"""
        if not self.enabled:
            return "Извините, ИИ-помощник временно недоступен. Используйте команды из меню."
        
        logger.info(f"🤖 Обработка запроса: {query}")
        
        # Определяем намерение
        intent = self.detect_intent(query)
        logger.info(f"🎯 Намерение: {intent}")
        
        # Извлекаем сущности
        entities = self.extract_entities(query)
        logger.info(f"🔍 Сущности: {entities}")
        
        # Получаем историю диалога
        history = []
        if self.db_client and user_id:
            history = self.db_client.get_conversation_history(user_id, limit=3)
        
        # Обрабатываем в зависимости от интента
        if intent == 'command':
            # Команды обрабатываются отдельно
            return "Используйте команды из меню для навигации."
        
        elif intent == 'greeting':
            import random
            return random.choice(self.response_templates['greeting'])
        
        elif intent == 'farewell':
            import random
            return random.choice(self.response_templates['farewell'])
        
        elif intent == 'tariff_info':
            return await self._handle_tariff_query(query, entities)
        
        elif intent == 'model_info':
            return await self._handle_model_query(query, entities)
        
        elif intent in ['portfolio_request', 'schedule_request', 'contact_request', 'thanks']:
            import random
            return random.choice(self.response_templates[intent])
        
        else:
            # Неизвестный запрос
            import random
            base_response = random.choice(self.response_templates['unknown'])
            
            # Предлагаем конкретные варианты на основе контекста
            suggestions = []
            
            if history:
                # Анализируем предыдущие сообщения
                last_messages = [msg['text'] for msg in history[-2:] if not msg['is_bot']]
                for msg in last_messages:
                    if any(word in msg.lower() for word in ['тариф', 'цена', 'стоит']):
                        suggestions.append("Может быть, вы хотите узнать о тарифах? Напишите 'тарифы'")
                        break
                    elif any(word in msg.lower() for word in ['модель', 'девушка', 'рост']):
                        suggestions.append("Может быть, вы спрашиваете о моделях? Напишите 'модели'")
                        break
            
            if not suggestions:
                suggestions.append("Вы можете спросить о тарифах, моделях или вызвать менеджера.")
            
            return f"{base_response}\n\n{suggestions[0]}"
    
    async def _handle_tariff_query(self, query: str, entities: Dict[str, Any]) -> str:
        """Обработка запроса о тарифах"""
        if not self.gsheets_client:
            return "Данные о тарифах временно недоступны. Попробуйте позже."
        
        tariffs = self.gsheets_client.cache.get("tariffs", [])
        synonyms = self.gsheets_client.cache.get("synonyms_dict", {})
        
        if not tariffs:
            return "Тарифы не найдены. Используйте команду /reload для загрузки данных."
        
        # Пробуем найти конкретный тариф
        found_tariff = self.gsheets_client.search_tariff(query, tariffs, synonyms)
        
        if found_tariff:
            # Форматируем ответ
            name = found_tariff.get("Название тарифа", "Без названия")
            price = found_tariff.get("Цена за 1 арт, руб.", "?")
            frames = found_tariff.get("Количество кадров", "?")
            desc = found_tariff.get("Описание", "")
            clients = found_tariff.get("Для каких клиентов", "")
            example = found_tariff.get("Пример ссылки", "")
            
            response = [
                f"<b>🎯 Тариф: {name}</b>",
                f"💰 <b>Цена:</b> {price}₽ за 1 артикул",
                f"📸 <b>Кадров:</b> {frames}",
            ]
            
            if desc:
                response.append(f"📝 <b>Описание:</b> {desc}")
            if clients:
                response.append(f"👥 <b>Для кого:</b> {clients}")
            if example and "http" in example:
                response.append(f"🔗 <b>Пример работ:</b> {example}")
            
            return "\n".join(response)
        else:
            # Если не нашли конкретный тариф, предлагаем посмотреть все
            return "Конкретный тариф не найден. Используйте команду /tariffs чтобы увидеть все доступные тарифы."
    
    async def _handle_model_query(self, query: str, entities: Dict[str, Any]) -> str:
        """Обработка запроса о моделях"""
        if not self.gsheets_client:
            return "Данные о моделях временно недоступны. Попробуйте позже."
        
        models = self.gsheets_client.cache.get("models", [])
        
        if not models:
            return "Модели не найдены. Используйте команду /reload для загрузки данных."
        
        # Пробуем найти конкретную модель
        found_model = self.gsheets_client.search_model(query, models)
        
        if found_model:
            # Форматируем ответ
            name = found_model.get("Имя", "Без имени")
            height = found_model.get("Рост", "?")
            params = found_model.get("Параметры", "")
            shooting = found_model.get("Тип съемок", "")
            portfolio = found_model.get("Ссылка на портфолио", "")
            dates = found_model.get("Свободные даты", "")
            
            response = [
                f"<b>👤 Модель: {name}</b>",
                f"📏 <b>Рост:</b> {height} см",
            ]
            
            if params:
                response.append(f"📐 <b>Параметры:</b> {params}")
            if shooting:
                response.append(f"🎬 <b>Тип съемок:</b> {shooting}")
            if dates:
                response.append(f"📅 <b>Свободные даты:</b> {dates}")
            if portfolio and "http" in portfolio:
                response.append(f"🔗 <b>Портфолио:</b> {portfolio}")
            
            return "\n".join(response)
        else:
            # Если не нашли конкретную модель, предлагаем посмотреть все
            return "Конкретная модель не найдена. Используйте команду /models чтобы увидеть всех моделей."
    
    def should_call_manager(self, query: str, intent: str) -> bool:
        """Определяет, нужно ли вызывать менеджера"""
        # Фразы, требующие менеджера
        manager_keywords = [
            'менеджер', 'человек', 'оператор', 'админ', 'администратор',
            'позовите', 'вызовите', 'нужен человек', 'живой',
            'договор', 'оплата', 'заказ', 'забронировать', 'записаться',
            'жалоба', 'проблема', 'недоволен', 'претензия'
        ]
        
        query_lower = query.lower()
        
        # Проверяем ключевые слова
        if any(keyword in query_lower for keyword in manager_keywords):
            return True
        
        # Проверяем интенты
        if intent in ['contact_request']:
            return True
        
        # Если пользователь повторяет вопрос несколько раз
        return False
    
    def generate_suggestions(self, query: str, intent: str) -> List[str]:
        """Генерация предложений для пользователя"""
        suggestions = []
        query_lower = query.lower()
        
        if intent == 'unknown':
            if 'стоит' in query_lower or 'цена' in query_lower:
                suggestions.append("💡 Попробуйте: 'Сколько стоит базовый тариф?'")
            elif 'модель' in query_lower or 'девушка' in query_lower:
                suggestions.append("💡 Попробуйте: 'Покажи модели для съемки'")
            elif 'когда' in query_lower or 'время' in query_lower:
                suggestions.append("💡 Попробуйте: 'Когда свободна Хлоя?'")
            else:
                suggestions.append("💡 Попробуйте: 'Тарифы' или 'Модели'")
        
        elif intent == 'tariff_info':
            suggestions.append("💡 Вы можете спросить: 'Базовый тариф' или 'Vata Prod'")
        
        elif intent == 'model_info':
            suggestions.append("💡 Вы можете спросить: 'Хлоя' или 'модели для мобильной съемки'")
        
        return suggestions