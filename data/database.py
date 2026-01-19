import sqlite3
import os
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class ConversationDatabase:
    """База данных для хранения истории диалогов"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Инициализация базы данных"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица сообщений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message_text TEXT,
                    is_bot BOOLEAN,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)')
            
            conn.commit()
            logger.info(f"✅ База данных инициализирована: {self.db_path}")
    
    def save_message(self, user_id: int, username: str, 
                    first_name: str, last_name: str, 
                    message: str, is_bot: bool = False):
        """Сохранение сообщения"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, last_activity)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, username, first_name, last_name))
                
                cursor.execute('''
                    INSERT INTO messages (user_id, message_text, is_bot)
                    VALUES (?, ?, ?)
                ''', (user_id, message, is_bot))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сообщения: {e}")
    
    def get_conversation_history(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Получение истории диалога"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT message_text, is_bot, timestamp
                    FROM messages 
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (user_id, limit))
                
                rows = cursor.fetchall()
                history = []
                
                for row in reversed(rows):
                    history.append({
                        'text': row['message_text'],
                        'is_bot': bool(row['is_bot']),
                        'timestamp': row['timestamp']
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории: {e}")
            return []
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получение статистики пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM messages WHERE user_id = ?', (user_id,))
                total = cursor.fetchone()[0] or 0
                
                cursor.execute('SELECT COUNT(*) FROM messages WHERE user_id = ? AND is_bot = 1', (user_id,))
                bot = cursor.fetchone()[0] or 0
                
                cursor.execute('SELECT MIN(timestamp) FROM messages WHERE user_id = ?', (user_id,))
                first = cursor.fetchone()[0]
                
                cursor.execute('SELECT last_activity FROM users WHERE user_id = ?', (user_id,))
                last = cursor.fetchone()
                
                return {
                    'total_messages': total,
                    'bot_messages': bot,
                    'user_messages': total - bot,
                    'first_message': first,
                    'last_activity': last[0] if last else None
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {}