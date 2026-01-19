# check_encoding.py
import os

def check_file_encoding(file_path):
    """Проверяет кодировку файла"""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            # Пробуем декодировать как UTF-8
            content.decode('utf-8')
            return True
    except UnicodeDecodeError as e:
        print(f"❌ Файл {file_path} не в UTF-8: {e}")
        return False

# Проверяем все .py файлы
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.py'):
            file_path = os.path.join(root, file)
            if check_file_encoding(file_path):
                print(f"✅ {file_path} - OK")