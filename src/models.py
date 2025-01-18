from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List
from config import WATER_PER_KG, WATER_PER_ACTIVITY, WATER_HOT_WEATHER

@dataclass
class DailyStats:
    date: str  # ISO format date string
    logged_water: float = 0
    logged_calories: float = 0
    burned_calories: float = 0
    water_goal: float = 0
    calorie_goal: float = 0
    temperature: float = 0
    food_log: List[Dict] = field(default_factory=list)
    workout_log: List[Dict] = field(default_factory=list)

@dataclass
class UserProfile:
    user_id: int
    weight: float = 0
    height: float = 0
    age: int = 0
    activity_minutes: int = 0
    city: str = ""
    daily_stats: Dict[str, DailyStats] = field(default_factory=dict)
    
    async def get_current_stats(self) -> DailyStats:
        """Gets or creates stats for current day"""
        today = datetime.now().date().isoformat()
        if today not in self.daily_stats:
            # Создаем новые статистики для дня
            self.daily_stats[today] = DailyStats(date=today)
            # Инициализируем цели для нового дня
            from utils import get_temperature  # Импорт здесь во избежание циклических зависимостей
            from config import WEATHER_API_KEY
            
            temp = await get_temperature(self.city, WEATHER_API_KEY)
            if temp is not None:
                await self.update_daily_goals(temp)
            else:
                # Если не удалось получить температуру, используем базовые цели
                stats = self.daily_stats[today]
                stats.water_goal = self.calculate_water_goal(20)  # Используем 20°C как базовую температуру
                stats.calorie_goal = self.calculate_calorie_goal()
                stats.temperature = 20
        
        return self.daily_stats[today]
    
    def calculate_water_goal(self, temperature: float) -> float:
        """Рассчитывает дневную норму воды в мл"""
        base = self.weight * WATER_PER_KG  # базовая норма
        activity = (self.activity_minutes // 30) * WATER_PER_ACTIVITY  # +500мл каждые 30 минут активности
        temp_addition = WATER_HOT_WEATHER if temperature > 25 else 0  # +500мл при жаркой погоде
        return base + activity + temp_addition

    def calculate_calorie_goal(self) -> float:
        """Рассчитывает дневную норму калорий"""
        bmr = 10 * self.weight + 6.25 * self.height - 5 * self.age
        activity_calories = self.activity_minutes * 4  # примерно 4 калории в минуту
        return bmr + activity_calories

    async def update_daily_goals(self, temperature: float):
        """Updates daily goals based on current conditions"""
        stats = await self.get_current_stats()
        stats.water_goal = self.calculate_water_goal(temperature)
        stats.calorie_goal = self.calculate_calorie_goal()
        stats.temperature = temperature
