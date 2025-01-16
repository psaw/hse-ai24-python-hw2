import aiohttp
from typing import Optional, Dict

async def get_temperature(city: str, api_key: str) -> Optional[float]:
    """Получает температуру для города через OpenWeatherMap API"""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data["main"]["temp"]
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
        print(f"Error getting food info: {e}")
    return None
