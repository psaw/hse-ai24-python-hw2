import os
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токены и ключи API
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# FatSecret
CONSUMER_KEY = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")

# Настройка логирования
logger = logging.getLogger('fitness_bot')
logger.setLevel(LOG_LEVEL)

# Создаем форматтер для логов
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Создаем обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Проверяем наличие необходимых переменных
if not all([BOT_TOKEN, WEATHER_API_KEY]):
    logger.error("Отсутствуют необходимые переменные окружения")
    raise ValueError("Отсутствуют необходимые переменные окружения")

# Константы для расчетов
WATER_PER_KG = 30  # мл воды на кг веса
WATER_PER_ACTIVITY = 500  # мл воды за каждые 30 минут базовой активности
WATER_PER_WORKOUT = 200  # мл воды за каждые 30 минут тренировки
WATER_HOT_WEATHER = 500  # дополнительная вода при жаркой погоде

# Калории, сжигаемые за минуту различных активностей
WORKOUT_CALORIES = {
    "run": 10,
    "walk": 5,
    "swim": 8,
    "bike": 7,
    "yoga": 3,
    "power": 6
}
