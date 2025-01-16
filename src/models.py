from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List
from config import WATER_PER_KG, WATER_PER_ACTIVITY, WATER_HOT_WEATHER

@dataclass
class UserProfile:
    user_id: int
    weight: float = 0
    height: float = 0
    age: int = 0
    activity_minutes: int = 0
    city: str = ""
    water_goal: float = 0
    calorie_goal: float = 0
    logged_water: float = 0
    logged_calories: float = 0
    burned_calories: float = 0
    food_log: List[Dict] = field(default_factory=list)
    workout_log: List[Dict] = field(default_factory=list)

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
