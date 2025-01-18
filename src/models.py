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
            # Create new stats for the day
            self.daily_stats[today] = DailyStats(date=today)
            # Initialize goals for new day
            from utils import get_temperature  # Import here to avoid circular dependencies
            from config import WEATHER_API_KEY
            
            temp = await get_temperature(self.city, WEATHER_API_KEY)
            if temp is not None:
                await self.update_daily_goals(temp)
            else:
                # If failed to get temperature, use base goals
                stats = self.daily_stats[today]
                stats.water_goal = self.calculate_water_goal(20)  # Use 20°C as base temperature
                stats.calorie_goal = self.calculate_calorie_goal()
                stats.temperature = 20
        
        return self.daily_stats[today]
    
    def calculate_water_goal(self, temperature: float) -> float:
        """Calculates daily water norm in ml"""
        base = self.weight * WATER_PER_KG  # base norm
        activity = (self.activity_minutes // 30) * WATER_PER_ACTIVITY  # +500ml every 30 minutes of activity
        temp_addition = WATER_HOT_WEATHER if temperature > 25 else 0  # +500ml in hot weather
        return base + activity + temp_addition

    def calculate_calorie_goal(self) -> float:
        """Calculates daily calorie norm"""
        bmr = 10 * self.weight + 6.25 * self.height - 5 * self.age
        activity_calories = self.activity_minutes * 4  # approximately 4 calories per minute
        return bmr + activity_calories

    async def update_daily_goals(self, temperature: float):
        """Updates daily goals based on current conditions"""
        stats = await self.get_current_stats()
        stats.water_goal = self.calculate_water_goal(temperature)
        stats.calorie_goal = self.calculate_calorie_goal()
        stats.temperature = temperature
