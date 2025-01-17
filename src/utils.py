import aiohttp
from typing import Optional, Dict
import matplotlib.pyplot as plt
import io
from datetime import datetime, timedelta
import numpy as np
from models import UserProfile
from config import logger, WEATHER_API_KEY


async def get_temperature(city: str, api_key: str) -> Optional[float]:
    """Получает температуру для города через OpenWeatherMap API"""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data["main"]["temp"]
            logger.error("Ошибка при получении температуры: {}".format(response.status))
    return None


async def get_food_info(product_name: str) -> Optional[Dict]:
    """Получает информацию о продукте через OpenFoodFacts API"""
    url = f"https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": product_name,
        "search_simple": 1,
        "action": "process",
        "fields": "product_name,nutriments",
        "json": 1,
        "page_size": 1
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("products"):
                        product = data["products"][0]
                        calories = product.get("nutriments", {}).get("energy-kcal_100g")
                        
                        # Проверяем, что калории - это число и оно больше 0
                        if calories and isinstance(calories, (int, float)) and calories > 0:
                            return {
                                "name": product.get("product_name", product_name).strip() or product_name,
                                "calories": float(calories)
                            }
    except Exception as e:
        logger.error("Error getting food info: {}".format(e))
    return None


async def generate_progress_charts(user_profile: UserProfile) -> io.BytesIO:
    """Генерирует графики прогресса по воде и калориям"""
    # Создаем фигуру с двумя подграфиками
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
    fig.patch.set_facecolor('#F0F2F6')
    
    # Цвета для графиков
    colors = ['#2E86C1', '#3498DB']
    
    # График воды
    water_data = [user_profile.logged_water, user_profile.water_goal]
    water_labels = ['Выпито', 'Цель']
    bars1 = ax1.bar(water_labels, water_data, color=colors)
    ax1.set_title('Прогресс по воде', pad=20, fontsize=14)
    ax1.set_ylabel('Миллилитры (мл)')
    
    # Добавляем значения над столбцами
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)} мл',
                ha='center', va='bottom')
    
    # График калорий
    calorie_data = [user_profile.logged_calories, user_profile.burned_calories, user_profile.calorie_goal]
    calorie_labels = ['Потреблено', 'Сожжено', 'Цель']
    bars2 = ax2.bar(calorie_labels, calorie_data, color=colors + ['#2ECC71'])
    ax2.set_title('Прогресс по калориям', pad=20, fontsize=14)
    ax2.set_ylabel('Калории (ккал)')
    
    # Добавляем значения над столбцами
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)} ккал',
                ha='center', va='bottom')
    
    # Стилизация графиков
    for ax in [ax1, ax2]:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        ax.set_facecolor('#F0F2F6')
    
    plt.tight_layout()
    
    # Сохраняем график в буфер
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf
