import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токены и ключи API
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Проверяем наличие необходимых переменных
if not all([BOT_TOKEN, WEATHER_API_KEY]):
    raise ValueError("Отсутствуют необходимые переменные окружения")

# Константы для расчетов
WATER_PER_KG = 30  # мл воды на кг веса
WATER_PER_ACTIVITY = 500  # мл воды за каждые 30 минут активности
WATER_HOT_WEATHER = 500  # дополнительная вода при жаркой погоде

# Калории, сжигаемые за минуту различных активностей
WORKOUT_CALORIES = {
    "бег": 10,
    "ходьба": 5,
    "плавание": 8,
    "велосипед": 7,
    "йога": 3,
    "силовая": 6
}
