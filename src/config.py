import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API tokens and keys
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# FatSecret
CONSUMER_KEY = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")

# Logging setup
logger = logging.getLogger('fitness_bot')
logger.setLevel(LOG_LEVEL)

# Create formatter for logs
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Create handler for console output
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Check for required environment variables
if not all([BOT_TOKEN, WEATHER_API_KEY, CONSUMER_KEY, CONSUMER_SECRET]):
    logger.error("Missing required environment variables")
    raise ValueError("Missing required environment variables")

# Constants for calculations
WATER_PER_KG = 30  # ml of water per kg of weight
WATER_PER_ACTIVITY = 500  # ml of water per 30 minutes of base activity
WATER_PER_WORKOUT = 200  # ml of water per 30 minutes of workout
WATER_HOT_WEATHER = 500  # additional water in hot weather

# Calories burned per minute for different activities
WORKOUT_CALORIES = {
    "run": 10,
    "walk": 5,
    "swim": 8,
    "bike": 7,
    "yoga": 3,
    "power": 6
}
