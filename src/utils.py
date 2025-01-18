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
    """Gets temperature for a city using OpenWeatherMap API
        Example response for Moscow:
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
            logger.error("Error getting temperature: {}".format(response.status))
    return None


async def get_food_info(product_name: str) -> Optional[Dict]:
    """Gets food information using OpenFoodFacts API"""
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
                        
                        # Check if calories is a number and greater than 0
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
    Gets food information using FatSecret API
    Args:
        product_name: food name
    Returns:
        Dict with food information or None if error

        Example content for coffee
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
        # Initialize FatSecret client
        fs = Fatsecret(CONSUMER_KEY, CONSUMER_SECRET)

        # Search for food. ENGLISH ONLY!
        search_results = fs.foods_search(product_name) #, region="RU", language="ru") - only in paid version

        if not search_results:
            logger.warning(f"Food not found: {product_name}")
            return None

        # Take first search result
        food_id = search_results[0]['food_id']

        # Get detailed food information
        food_details = fs.food_get_v2(food_id)

        if not food_details or 'servings' not in food_details:
            logger.warning(f"No serving information for food: {product_name}")
            return None

        # Get serving information
        servings = food_details['servings']['serving']
        # Looking for 100g serving
        serving_100g = None
        if isinstance(servings, list):
            for s in servings:
                if (s.get('metric_serving_unit') == 'g' and 
                    float(s.get('metric_serving_amount', 0)) == 100):
                    serving_100g = s
                    break
        
        # If found 100g serving, use it
        if serving_100g:
            serving = serving_100g
            factor = 1
        else:  # otherwise take first serving
            serving = servings[0] if isinstance(servings, list) else servings
            # If serving is in ounces, convert to grams (1 oz = 28.35 g)
            if serving.get('metric_serving_unit') == 'oz':
                metric_amount = float(serving.get('metric_serving_amount', 0)) * 28.35
                serving['metric_serving_unit'] = 'g'
            else:
                metric_amount = float(serving.get('metric_serving_amount', 100))
            # If serving is not 100g, convert to 100g
            factor = 100 / metric_amount

        # Format result for 100g
        return {
            "name": food_details.get('food_name', product_name),
            "calories": round(float(serving.get('calories', 0))*factor),  # kcal per 100g, round to integer
            "protein": round(float(serving.get('protein', 0))*factor, 1),  # protein per 100g, round to 1 decimal
            "fat": round(float(serving.get('fat', 0))*factor, 1),  # fat per 100g, round to 1 decimal
            "carbohydrate": round(float(serving.get('carbohydrate', 0))*factor, 1),  # carbs per 100g, round to 1 decimal
            "metric_serving_unit": serving.get('metric_serving_unit', 'g'),  # measurement unit
        }
    except KeyError as e:
        logger.error("Error getting food information '{}' : {}".format(product_name, str(e)))
        return {"error": str(e), "name": product_name, "suggest": "Please use English food names only"}
    except Exception as e:
        logger.error("Error getting food information '{}' : {}".format(product_name, str(e)))
        return {"error": str(e), "name": product_name}


async def generate_progress_charts(stats: DailyStats) -> io.BytesIO:
    """Generates progress charts for water and calories"""
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
    fig.patch.set_facecolor('#F0F2F6')
    
    # Colors for charts
    colors = ['#2E86C1', '#3498DB']
    
    # Water chart
    water_data = [stats.logged_water, stats.water_goal]
    water_labels = ['Consumed', 'Goal']
    bars1 = ax1.bar(water_labels, water_data, color=colors)
    ax1.set_title('Water Progress', pad=20, fontsize=14)
    ax1.set_ylabel('Milliliters (ml)')
    
    # Add values above bars
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)} ml',
                ha='center', va='bottom')
    
    # Calories chart
    calorie_data = [stats.logged_calories, stats.burned_calories, stats.calorie_goal]
    calorie_labels = ['Consumed', 'Burned', 'BMR']
    bars2 = ax2.bar(calorie_labels, calorie_data, color=colors + ['#2ECC71'])
    ax2.set_title('Calorie Progress', pad=20, fontsize=14)
    ax2.set_ylabel('Calories (kcal)')
    
    # Add values above bars
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)} kcal',
                ha='center', va='bottom')
    
    # Style charts
    for ax in [ax1, ax2]:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        ax.set_facecolor('#F0F2F6')
    
    plt.tight_layout()
    
    # Save chart to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf
