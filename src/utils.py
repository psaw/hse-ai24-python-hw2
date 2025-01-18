import aiohttp
from typing import Optional, Dict
import matplotlib.pyplot as plt
import io
from datetime import datetime, timedelta
import numpy as np
from models import DailyStats
from config import logger, WEATHER_API_KEY, CONSUMER_KEY, CONSUMER_SECRET
from fatsecret import Fatsecret


async def get_temperature(city: str, api_key: str) -> Optional[float]:
    """Получает температуру для города через OpenWeatherMap API
        Пример ответа для Moscow:
            {
                "coord": {"lon": 37.6156, "lat": 55.7522},
                "weather": [{
                    "id": 804,
                    "main": "Clouds",
                    "description": "overcast clouds", 
                    "icon": "04n"
                }],
                "main": {
                    "temp": 1.94,
                    "feels_like": -3.23,
                    "temp_min": 1.24,
                    "temp_max": 2.04,
                    "pressure": 1007,
                    "humidity": 78
                },
                "wind": {"speed": 6.55, "deg": 315},
                "rain": {"1h": 0.1},
                "clouds": {"all": 97},
                "sys": {
                    "country": "RU",
                    "sunrise": 1737179143,
                    "sunset": 1737207226
                },
                "name": "Moscow",
                "cod": 200
            }
    """
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


async def get_food_info_from_fs(product_name: str) -> Optional[Dict]:
    """
    Получает информацию о продукте через FatSecret API
    Args:
        product_name: название продукта
    Returns:
        Dict с информацией о продукте или None в случае ошибки

        Пример содержимого для coffee
        serving = 
        {
            'calcium': '5',
            'calories': '2', 
            'carbohydrate': '0.09',
            'cholesterol': '0',
            'fat': '0.05',
            'fiber': '0',
            'iron': '0.05',
            'measurement_description': 'mug (8 fl oz)',
            'metric_serving_amount': '237.000',
            'metric_serving_unit': 'g',
            'monounsaturated_fat': '0.028',
            'number_of_units': '1.000',
            'polyunsaturated_fat': '0.002',
            'potassium': '111',
            'protein': '0.28',
            'saturated_fat': '0.005',
            'serving_description': '1 mug (8 fl oz)',
            'serving_id': '27699',
            'serving_url': 'https://www.fatsecret.com/calories-nutrition/generic/coffee?portionid=27699&portionamount=1.000',
            'sodium': '5',
            'sugar': '0',
            'vitamin_a': '0',
            'vitamin_c': '0.0'
        }
    """
    try:
        # Инициализация клиента FatSecret
        fs = Fatsecret(CONSUMER_KEY, CONSUMER_SECRET)

        # Поиск продукта. Только ПО-АНГЛИЙСКИЙ!
        search_results = fs.foods_search(product_name) #, region="RU", language="ru") - только в платной версии

        if not search_results:
            logger.warning(f"Продукт не найден: {product_name}")
            return None

        # Берем первый результат поиска
        food_id = search_results[0]['food_id']

        # Получаем детальную информацию о продукте
        food_details = fs.food_get_v2(food_id)

        if not food_details or 'servings' not in food_details:
            logger.warning(f"Нет информации о порциях для продукта: {product_name}")
            return None

        # Получаем информацию о порциях
        servings = food_details['servings']['serving']
        # Ищем порцию на 100г
        serving_100g = None
        if isinstance(servings, list):
            for s in servings:
                if (s.get('metric_serving_unit') == 'g' and 
                    float(s.get('metric_serving_amount', 0)) == 100):
                    serving_100g = s
                    break
        
        # Если нашли порцию на 100г, используем её
        if serving_100g:
            serving = serving_100g
            factor = 1
        else:  # иначе берем первую порцию
            serving = servings[0] if isinstance(servings, list) else servings
            # Если порция в унциях, переводим в граммы (1 oz = 28.35 г)
            if serving.get('metric_serving_unit') == 'oz':
                metric_amount = float(serving.get('metric_serving_amount', 0)) * 28.35
                serving['metric_serving_unit'] = 'г'
            else:
                metric_amount = float(serving.get('metric_serving_amount', 100))
            # Если порция не на 100г, будем приводить к 100г
            factor = 100 / metric_amount

        # Формируем результат для 100г
        return {
            "name": food_details.get('food_name', product_name),
            "calories": round(float(serving.get('calories', 0))*factor),  # ккал на 100г, округляем до целого
            "protein": round(float(serving.get('protein', 0))*factor, 1),  # белки на 100г, .. до 1 знака
            "fat": round(float(serving.get('fat', 0))*factor, 1),  # жиры на 100г, .. до 1 знака
            "carbohydrate": round(float(serving.get('carbohydrate', 0))*factor, 1),  # углеводы на 100г, .. до 1 знака
            "metric_serving_unit": serving.get('metric_serving_unit', 'г'),  # единица измерения
        }
    except KeyError as e:
        logger.error("Ошибка при получении информации о продукте '{}' : {}".format(product_name, str(e)))
        return {"error": str(e), "name": product_name, "suggest": "Используйте только английские названия продуктов"}
    except Exception as e:
        logger.error("Ошибка при получении информации о продукте '{}' : {}".format(product_name, str(e)))
        return {"error": str(e), "name": product_name}


async def generate_progress_charts(stats: DailyStats) -> io.BytesIO:
    """Генерирует графики прогресса по воде и калориям"""
    # Создаем фигуру с двумя подграфиками
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
    fig.patch.set_facecolor('#F0F2F6')
    
    # Цвета для графиков
    colors = ['#2E86C1', '#3498DB']
    
    # График воды
    water_data = [stats.logged_water, stats.water_goal]
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
    calorie_data = [stats.logged_calories, stats.burned_calories, stats.calorie_goal]
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
