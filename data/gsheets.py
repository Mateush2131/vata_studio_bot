# data/gsheets.py - упрощенная версия для теста
import logging
import csv
import asyncio
from io import StringIO
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiohttp

logger = logging.getLogger(__name__)

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
                reader = csv.DictReader(StringIO(content))
                
                for row in reader:
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
            synonyms_dict = self._parse_synonyms(results["synonyms"])
            results["synonyms_dict"] = synonyms_dict
            logger.info(f"📝 Синонимов: {len(synonyms_dict)} групп")
        
        return results
    
    def _parse_synonyms(self, synonyms_data: List[Dict]) -> Dict[str, List[str]]:
        """Парсинг синонимов"""
        synonyms_dict = {}
        
        for row in synonyms_data:
            for key, value in row.items():
                if value and 'синон' in key.lower():
                    words = [word.strip().lower() for word in value.split(',') if word.strip()]
                    if words:
                        main_word = words[0]
                        synonyms_dict[main_word] = words[1:] if len(words) > 1 else []
        
        return synonyms_dict