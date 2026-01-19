import logging
from typing import List, Dict, Any
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class ManagerNotifier:
    """Система уведомления менеджеров"""
    
    def __init__(self, bot=None, manager_ids: List[int] = None):
        self.bot = bot
        self.manager_ids = manager_ids or []
        self.pending_notifications = []
        self.enabled = True
        
        # Статистика
        self.stats = {
            'total_calls': 0,
            'handled_calls': 0,
            'avg_response_time': 0,
            'last_notification': None
        }
        
        logger.info(f"📞 Система уведомлений инициализирована. Менеджеров: {len(self.manager_ids)}")
    
    async def notify_manager(self, user_id: int, username: str, 
                           first_name: str, last_name: str, 
                           question: str, context: List[Dict] = None):
        """Уведомление менеджера о вызове"""
        if not self.enabled or not self.bot or not self.manager_ids:
            logger.info(f"📞 Вызов менеджера (система отключена): user_id={user_id}, вопрос: {question[:50]}...")
            return False
        
        self.stats['total_calls'] += 1
        self.stats['last_notification'] = datetime.now()
        
        # Формируем сообщение для менеджера
        user_info = f"👤 Пользователь: {first_name} {last_name}"
        if username:
            user_info += f" (@{username})"
        user_info += f" (ID: {user_id})"
        
        question_text = f"❓ Вопрос: {question}"
        
        # Добавляем контекст если есть
        context_text = ""
        if context:
            context_text = "\n\n📜 Контекст диалога:\n"
            for msg in context[-3:]:  # Последние 3 сообщения
                sender = "Бот" if msg.get('is_bot') else "Пользователь"
                text = msg.get('text', '')[:100]
                context_text += f"{sender}: {text}\n"
        
        # Формируем полное сообщение
        message = f"""
🚨 ВНИМАНИЕ: Вызов менеджера!

{user_info}
{question_text}
{context_text}

⚠️ Требуется вмешательство менеджера!
        """
        
        # Отправляем всем менеджерам
        success = False
        for manager_id in self.manager_ids:
            try:
                await self.bot.send_message(
                    chat_id=manager_id,
                    text=message,
                    parse_mode="HTML"
                )
                logger.info(f"✅ Уведомление отправлено менеджеру {manager_id}")
                success = True
                
                # Добавляем в pending для отслеживания
                self.pending_notifications.append({
                    'user_id': user_id,
                    'manager_id': manager_id,
                    'question': question,
                    'timestamp': datetime.now(),
                    'handled': False
                })
                
            except Exception as e:
                logger.error(f"❌ Ошибка отправки уведомления менеджеру {manager_id}: {e}")
        
        if success:
            # Отправляем пользователю подтверждение
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text="✅ <b>Менеджер уведомлен!</b>\n\nС вами свяжутся в ближайшее время. А пока могу помочь с другими вопросами?",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"❌ Ошибка отправки подтверждения пользователю: {e}")
        
        return success
    
    async def notify_typing_timeout(self, user_id: int, username: str, 
                                  first_name: str, last_name: str):
        """Уведомление о длительном наборе текста пользователем"""
        if not self.enabled or not self.bot or not self.manager_ids:
            return
        
        message = f"""
⏰ ВНИМАНИЕ: Долгий набор текста

👤 Пользователь: {first_name} {last_name} (@{username})
🆔 ID: {user_id}

Пользователь долго набирает сообщение. Возможно, нужна помощь или есть сложный вопрос.
        """
        
        for manager_id in self.manager_ids[:1]:  # Только первому менеджеру
            try:
                await self.bot.send_message(
                    chat_id=manager_id,
                    text=message,
                    parse_mode="HTML"
                )
                logger.info(f"⏰ Уведомление о таймауте отправлено менеджеру {manager_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки уведомления о таймауте: {e}")
    
    def mark_notification_handled(self, user_id: int, manager_id: int = None):
        """Отметить уведомление как обработанное"""
        for notification in self.pending_notifications:
            if notification['user_id'] == user_id and not notification['handled']:
                if manager_id is None or notification['manager_id'] == manager_id:
                    notification['handled'] = True
                    notification['handled_at'] = datetime.now()
                    
                    # Обновляем статистику
                    self.stats['handled_calls'] += 1
                    
                    response_time = (notification['handled_at'] - notification['timestamp']).seconds
                    # Обновляем среднее время ответа
                    if self.stats['avg_response_time'] == 0:
                        self.stats['avg_response_time'] = response_time
                    else:
                        self.stats['avg_response_time'] = (self.stats['avg_response_time'] + response_time) / 2
                    
                    logger.info(f"✅ Уведомление отмечено как обработанное. Время ответа: {response_time} сек")
                    return True
        
        return False
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Получение статистики уведомлений"""
        pending = len([n for n in self.pending_notifications if not n['handled']])
        
        return {
            'total_calls': self.stats['total_calls'],
            'handled_calls': self.stats['handled_calls'],
            'pending_calls': pending,
            'avg_response_time': self.stats['avg_response_time'],
            'last_notification': self.stats['last_notification']
        }
    
    def cleanup_old_notifications(self, hours: int = 24):
        """Очистка старых уведомлений"""
        now = datetime.now()
        old_count = 0
        
        self.pending_notifications = [
            n for n in self.pending_notifications
            if (now - n['timestamp']).total_seconds() < hours * 3600
        ]
        
        old_count = len(self.pending_notifications) - len(self.pending_notifications)
        if old_count > 0:
            logger.info(f"🧹 Очищено {old_count} старых уведомлений")
    
    async def send_manager_stats(self, manager_id: int):
        """Отправка статистики менеджеру"""
        if not self.bot:
            return
        
        stats = self.get_notification_stats()
        
        message = f"""
📊 <b>Статистика уведомлений</b>

• Всего вызовов: {stats['total_calls']}
• Обработано: {stats['handled_calls']}
• Ожидают: {stats['pending_calls']}
• Среднее время ответа: {stats['avg_response_time']:.1f} сек
• Последний вызов: {stats['last_notification'].strftime('%H:%M') if stats['last_notification'] else 'нет'}

<b>Текущие ожидающие:</b>
        """
        
        pending = [n for n in self.pending_notifications if not n['handled']]
        if pending:
            for i, n in enumerate(pending[:5], 1):
                time_ago = (datetime.now() - n['timestamp']).seconds // 60
                message += f"\n{i}. Пользователь {n['user_id']} - {time_ago} мин назад"
        else:
            message += "\n✅ Нет ожидающих вызовов"
        
        try:
            await self.bot.send_message(
                chat_id=manager_id,
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка отправки статистики: {e}")