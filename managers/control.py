import logging
from typing import Dict, List, Any, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BotController:
    """Контроллер для управления состоянием бота"""
    
    def __init__(self):
        self.enabled_users: Set[int] = set()  # Пользователи с включенным ботом
        self.disabled_users: Set[int] = set() # Пользователи с отключенным ботом
        self.user_sessions: Dict[int, Dict[str, Any]] = {}  # Активные сессии
        self.manager_overrides: Dict[int, List[int]] = {}   # Менеджеры, переопределившие пользователей
        
        # Настройки по умолчанию
        self.settings = {
            'auto_enable_new_users': True,
            'session_timeout_minutes': 30,
            'max_messages_per_minute': 10,
            'typing_timeout_seconds': 30,
            'enable_ai_by_default': True
        }
        
        # Статистика
        self.stats = {
            'total_sessions': 0,
            'active_sessions': 0,
            'disabled_sessions': 0,
            'ai_responses': 0,
            'manager_interventions': 0
        }
        
        logger.info("🎛️ Контроллер бота инициализирован")
    
    def is_bot_enabled_for_user(self, user_id: int) -> bool:
        """Проверка, включен ли бот для пользователя"""
        if user_id in self.disabled_users:
            return False
        if user_id in self.enabled_users:
            return True
        
        # Новый пользователь - применяем настройку по умолчанию
        if self.settings['auto_enable_new_users']:
            self.enable_bot_for_user(user_id)
            return True
        
        return False
    
    def enable_bot_for_user(self, user_id: int, manager_id: int = None) -> bool:
        """Включение бота для пользователя"""
        if user_id in self.disabled_users:
            self.disabled_users.remove(user_id)
        
        self.enabled_users.add(user_id)
        
        # Записываем переопределение если было от менеджера
        if manager_id:
            if manager_id not in self.manager_overrides:
                self.manager_overrides[manager_id] = []
            if user_id not in self.manager_overrides[manager_id]:
                self.manager_overrides[manager_id].append(user_id)
            
            self.stats['manager_interventions'] += 1
        
        # Создаем или обновляем сессию
        self._create_or_update_session(user_id)
        
        logger.info(f"✅ Бот включен для user_id={user_id}" + 
                   (f" менеджером {manager_id}" if manager_id else ""))
        return True
    
    def disable_bot_for_user(self, user_id: int, manager_id: int = None) -> bool:
        """Отключение бота для пользователя"""
        if user_id in self.enabled_users:
            self.enabled_users.remove(user_id)
        
        self.disabled_users.add(user_id)
        
        # Записываем переопределение если было от менеджера
        if manager_id:
            if manager_id not in self.manager_overrides:
                self.manager_overrides[manager_id] = []
            if user_id not in self.manager_overrides[manager_id]:
                self.manager_overrides[manager_id].append(user_id)
            
            self.stats['manager_interventions'] += 1
        
        # Закрываем сессию
        if user_id in self.user_sessions:
            self.user_sessions[user_id]['active'] = False
            self.user_sessions[user_id]['ended_at'] = datetime.now()
            self.stats['active_sessions'] -= 1
            self.stats['disabled_sessions'] += 1
        
        logger.info(f"⛔ Бот отключен для user_id={user_id}" + 
                   (f" менеджером {manager_id}" if manager_id else ""))
        return True
    
    def toggle_bot_for_user(self, user_id: int, manager_id: int = None) -> bool:
        """Переключение состояния бота для пользователя"""
        if self.is_bot_enabled_for_user(user_id):
            return self.disable_bot_for_user(user_id, manager_id)
        else:
            return self.enable_bot_for_user(user_id, manager_id)
    
    def _create_or_update_session(self, user_id: int):
        """Создание или обновление сессии пользователя"""
        now = datetime.now()
        
        if user_id not in self.user_sessions:
            # Новая сессия
            self.user_sessions[user_id] = {
                'started_at': now,
                'last_activity': now,
                'message_count': 0,
                'ai_responses': 0,
                'active': True,
                'typing_started': None,
                'typing_timeouts': 0
            }
            self.stats['total_sessions'] += 1
            self.stats['active_sessions'] += 1
        else:
            # Обновление существующей сессии
            self.user_sessions[user_id]['last_activity'] = now
            
            # Если сессия была неактивна, возобновляем
            if not self.user_sessions[user_id]['active']:
                self.user_sessions[user_id]['active'] = True
                self.user_sessions[user_id]['started_at'] = now
                self.stats['active_sessions'] += 1
                self.stats['disabled_sessions'] -= 1
    
    def record_user_message(self, user_id: int):
        """Запись сообщения пользователя"""
        self._create_or_update_session(user_id)
        
        session = self.user_sessions[user_id]
        session['message_count'] += 1
        session['last_activity'] = datetime.now()
    
    def record_ai_response(self, user_id: int):
        """Запись ответа ИИ"""
        if user_id in self.user_sessions:
            self.user_sessions[user_id]['ai_responses'] += 1
            self.stats['ai_responses'] += 1
    
    def start_typing_timer(self, user_id: int):
        """Старт таймера набора текста"""
        if user_id in self.user_sessions:
            self.user_sessions[user_id]['typing_started'] = datetime.now()
    
    def stop_typing_timer(self, user_id: int):
        """Остановка таймера набора текста"""
        if user_id in self.user_sessions:
            self.user_sessions[user_id]['typing_started'] = None
    
    def check_typing_timeout(self, user_id: int) -> bool:
        """Проверка таймаута набора текста"""
        if user_id not in self.user_sessions:
            return False
        
        session = self.user_sessions[user_id]
        if not session['typing_started']:
            return False
        
        timeout_seconds = self.settings['typing_timeout_seconds']
        time_typing = (datetime.now() - session['typing_started']).seconds
        
        if time_typing > timeout_seconds:
            session['typing_timeouts'] += 1
            session['typing_started'] = None
            return True
        
        return False
    
    def check_message_rate_limit(self, user_id: int) -> bool:
        """Проверка ограничения скорости сообщений"""
        if user_id not in self.user_sessions:
            return True
        
        session = self.user_sessions[user_id]
        max_per_minute = self.settings['max_messages_per_minute']
        
        # Здесь можно добавить сложную логику ограничения скорости
        # Пока просто возвращаем True (не ограничиваем)
        return True
    
    def cleanup_inactive_sessions(self):
        """Очистка неактивных сессий"""
        now = datetime.now()
        timeout_minutes = self.settings['session_timeout_minutes']
        removed_count = 0
        
        inactive_users = []
        for user_id, session in self.user_sessions.items():
            if session['active']:
                inactive_time = (now - session['last_activity']).seconds // 60
                if inactive_time > timeout_minutes:
                    inactive_users.append(user_id)
        
        for user_id in inactive_users:
            self.user_sessions[user_id]['active'] = False
            self.user_sessions[user_id]['ended_at'] = now
            self.stats['active_sessions'] -= 1
            removed_count += 1
        
        if removed_count > 0:
            logger.info(f"🧹 Очищено {removed_count} неактивных сессий")
    
    def get_user_session_info(self, user_id: int) -> Dict[str, Any]:
        """Получение информации о сессии пользователя"""
        if user_id not in self.user_sessions:
            return None
        
        session = self.user_sessions[user_id].copy()
        
        # Добавляем вычисляемые поля
        now = datetime.now()
        session_duration = (now - session['started_at']).seconds // 60
        inactive_time = (now - session['last_activity']).seconds // 60 if session['last_activity'] else 0
        
        session['session_duration_minutes'] = session_duration
        session['inactive_minutes'] = inactive_time
        session['messages_per_minute'] = session['message_count'] / max(session_duration, 1)
        
        return session
    
    def get_controller_stats(self) -> Dict[str, Any]:
        """Получение статистики контроллера"""
        return {
            **self.stats,
            'enabled_users': len(self.enabled_users),
            'disabled_users': len(self.disabled_users),
            'active_sessions': self.stats['active_sessions'],
            'settings': self.settings
        }
    
    def update_setting(self, setting_name: str, value: Any) -> bool:
        """Обновление настройки контроллера"""
        if setting_name in self.settings:
            old_value = self.settings[setting_name]
            self.settings[setting_name] = value
            logger.info(f"⚙️ Настройка '{setting_name}' изменена: {old_value} -> {value}")
            return True
        return False
    
    def get_users_by_manager(self, manager_id: int) -> List[int]:
        """Получение пользователей, переопределенных менеджером"""
        return self.manager_overrides.get(manager_id, [])