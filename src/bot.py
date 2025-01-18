import asyncio
from aiogram import Bot, Dispatcher, Router, types, BaseMiddleware
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import BOT_TOKEN, WATER_PER_WORKOUT, WEATHER_API_KEY, WORKOUT_CALORIES, logger
from models import UserProfile
from utils import get_temperature, get_food_info, generate_progress_charts, get_food_info_from_fs
from datetime import datetime, timedelta


# FSM states for profile setup
class ProfileSetup(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()

# FSM states for food logging
class FoodLogging(StatesGroup):
    waiting_for_weight = State()
    waiting_for_food_name = State()

# FSM state for water logging
class WaterLogging(StatesGroup):
    waiting_for_water = State()

# FSM state for workout logging
class WorkoutLogging(StatesGroup):
    waiting_for_workout_type = State()
    waiting_for_workout_duration = State()
    commit_workout = State()

# FSM state for history period selection
class HistoryPeriod(StatesGroup):
    waiting_for_period = State()

# User data storage
users: dict[int, UserProfile] = {}

router = Router()


# Middleware for checking user profile existence
class CheckUserProfileMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        user_id = event.from_user.id
        
        # List of commands allowed without profile
        allowed_commands = ['/set_profile', '/start', '/help']
        
        # Skip if command is allowed or state is "profile setup"
        if ((event.text and any(event.text.startswith(cmd) for cmd in allowed_commands)) or 
            isinstance(data.get('state'), ProfileSetup) or
            data.get('raw_state') is not None and data['raw_state'].startswith('ProfileSetup')):
            return await handler(event, data)
            
        # Check if profile exists
        if user_id not in users:
            await event.answer("Please set up your profile first using /set_profile")
            return
            
        return await handler(event, data)


# Middleware for logging
class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        logger.info(f"Message from {event.from_user.id}: {event.text}")
        return await handler(event, data)

# Register middleware
router.message.middleware(LoggingMiddleware())
router.message.middleware(CheckUserProfileMiddleware()) 

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Hi! I'll help you track your water and calorie intake.\n"
        "Use the following commands:\n"
        "/set_profile - set up profile 👤\n"
        "/log_water <ml> - log water intake 💧\n"
        "/log_food <food> - log food intake 🍽\n"
        "/log_workout <type> <minutes> - log workout 🏃‍♂️\n"
        "/check_progress - check progress 🏁\n"
        "/charts - show progress charts 📊\n"
        "/history - show activity history 📅"
)
    
@router.message(Command("set_profile"))
async def cmd_set_profile(message: Message, state: FSMContext):
    await state.set_state(ProfileSetup.weight)
    await message.answer("Enter your weight (kg):")

@router.message(ProfileSetup.weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
        await state.update_data(weight=weight)
        await state.set_state(ProfileSetup.height)
        await message.answer("Enter your height (cm):")
    except ValueError:
        await message.answer("Please enter a number. Try again:")

@router.message(ProfileSetup.height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = float(message.text)
        await state.update_data(height=height)
        await state.set_state(ProfileSetup.age)
        await message.answer("Enter your age:")
    except ValueError:
        await message.answer("Please enter a number. Try again:")

@router.message(ProfileSetup.age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        await state.update_data(age=age)
        await state.set_state(ProfileSetup.activity)
        await message.answer("How many minutes of activity do you have per day?")
    except ValueError:
        await message.answer("Please enter a whole number. Try again:")
    
@router.message(ProfileSetup.activity)
async def process_activity(message: Message, state: FSMContext):
    try:
        activity = int(message.text)
        await state.update_data(activity=activity)
        await state.set_state(ProfileSetup.city)
        await message.answer("What city are you in?")
    except ValueError:
        await message.answer("Please enter a whole number of minutes. Try again:")
    
@router.message(ProfileSetup.city)
async def process_city(message: Message, state: FSMContext):
    city = message.text
    user_data = await state.get_data()
    user_id = message.from_user.id
    
    # Create user profile
    profile = UserProfile(
        user_id=user_id,
        weight=user_data['weight'],
        height=user_data['height'],
        age=user_data['age'],
        activity_minutes=user_data['activity'],
        city=city
    )

    try:
        # Get temperature for water norm calculation
        temp = await get_temperature(city, WEATHER_API_KEY)
        if temp is None:
            raise ValueError("Failed to get temperature")

        # Save profile before initializing statistics
        users[user_id] = profile
        
        # Initialize current day statistics
        stats = await profile.get_current_stats()
        
        await state.clear()  # Clear state
        logger.info(f"Profile set up for user {user_id}")
        await message.answer(
            "✅ Profile set up!\n"
            f"💧 Water goal: {stats.water_goal:.0f} ml\n"
            f"🔥 Calorie goal: {stats.calorie_goal:.0f} kcal\n\n"
            "Use the following commands:\n"
            "/log_water <ml> - log water intake 💧\n"
            "/log_food <food> - log food intake 🍽\n"
            "/log_workout <type> <minutes> - log workout 🏃‍♂️\n"
            "/check_progress - check progress 🏁\n"
            "/charts - show progress charts 📊\n"
            "/history - show activity history 📅"
        )
    except Exception as e:
        logger.error(f"Error setting up profile: {e}")
        await message.answer(
            "❌ Failed to get weather data.\n"
            "Please check the city name and try again.\n"
            "For example: Moscow, London, New York"
        )

@router.message(Command("log_water"))
async def cmd_log_water(message: Message, command: CommandObject, state: FSMContext):
    logger.debug(f"command.args: {command.args}")
    if not command.args:
        await state.set_state(WaterLogging.waiting_for_water)
        await message.answer("Please enter the amount of water consumed in ml:")
        return

    user_id = message.from_user.id
    stats = await users[user_id].get_current_stats()

    water_text = command.args
    logger.debug(f"water_text: {water_text}")
    try:
        water_amount = float(water_text)
        stats.logged_water += water_amount
        remaining = stats.water_goal - stats.logged_water
        await message.answer(
            f"✅ Logged: {water_amount} ml of water\n"
            f"💧 Remaining to drink: {max(0, remaining)} ml"
        )
    except ValueError:
        await message.answer("Please enter a valid number.")

@router.message(WaterLogging.waiting_for_water)
async def process_water_logging(message: Message, state: FSMContext):
    await state.clear()  # Clear state before processing
    # Passing value from message.text to cmd_log_water via CommandObject.args, so it's safe to clear state
    await cmd_log_water(message, CommandObject(prefix="/", command="log_water", args=message.text), state)


@router.message(Command("log_food"))
async def cmd_log_food(message: Message, command: CommandObject, state: FSMContext):
    logger.debug(f"command.args: {command.args}")
    if not command.args:
        await state.set_state(FoodLogging.waiting_for_food_name)
        await message.answer(
            "Please enter the food name (in English)."
        )
        return

    user_id = message.from_user.id

    # OpenFoodFacts API call
    # food_info = await get_food_info(command.args)

    # FatSecret API call
    food_info = await get_food_info_from_fs(command.args)

    if not food_info:
        logger.error("Food not found: {}".format(command.args))
        await message.answer(
            "Sorry, couldn't find information about this food.\n"
            "Try another food or check the spelling."
        )
        return
    if food_info.get("error"):
        error_message = f"Error getting food information: {food_info['name']}\n"
        error_message += "Try another food or check the spelling."
        if food_info.get("suggest"):
            error_message += f"\n**Note**: {food_info['suggest']}"
        await message.answer(error_message)
        return
    try:
        await state.update_data(
            food_name=food_info["name"],
            calories_per_100=float(food_info["calories"])
        )
        await state.set_state(FoodLogging.waiting_for_weight)
        await message.answer(
            f"🍎 {food_info['name']}\n"
            f"Calories: {food_info['calories']:.1f} kcal/100g\n"
            "How many grams did you eat?"
        )
    except Exception as e:
        logger.error(f"Error processing food information: {e}")
        await message.answer(
            "An error occurred while processing food information.\n"
            "Please try another food."
        )


@router.message(FoodLogging.waiting_for_food_name)
async def process_food_name(message: Message, state: FSMContext):
    await state.clear()  # Clear state before processing
    await cmd_log_food(message, CommandObject(prefix="/", command="log_food", args=message.text), state)
    

@router.message(FoodLogging.waiting_for_weight)
async def process_food_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
        food_data = await state.get_data()
        calories = food_data['calories_per_100'] * weight / 100
        
        user_id = message.from_user.id
        stats = await users[user_id].get_current_stats()
        stats.logged_calories += calories
        stats.food_log.append({
            "name": food_data['food_name'],
            "weight": weight,
            "calories": calories,
            "timestamp": datetime.now().isoformat()
        })
        
        await state.clear()
        await message.answer(
            f"✅ Logged: {food_data['food_name']}\n"
            f"- Weight: {weight} g\n"
            f"- Calories: {calories:.1f} kcal"
        )
    except ValueError:
        await message.answer("Please enter the weight in grams as a number.")


async def validate_workout_type(message: Message, workout_type: str | None) -> bool:
    """Checks the validity of the workout type and sends a message if the type is invalid"""
    if not workout_type or workout_type not in WORKOUT_CALORIES:
        await message.answer(
            "Unknown workout type.\n"
            "Available types: " + ", ".join(WORKOUT_CALORIES.keys())
        )
        return False
    return True

@router.message(WorkoutLogging.waiting_for_workout_type)
async def process_workout_type(message: Message, state: FSMContext):
    logger.debug(f":: WorkoutLogging.waiting_for_workout_type : message.text: {message.text}")
    if not await validate_workout_type(message, message.text):
        return
    
    await state.update_data(workout_type=message.text)
    await state.set_state(WorkoutLogging.waiting_for_workout_duration)
    await message.answer("How many minutes did you workout?")


@router.message(WorkoutLogging.waiting_for_workout_duration)
async def process_workout_duration(message: Message, state: FSMContext):
    logger.debug(f":: WorkoutLogging.waiting_for_workout_duration : message.text: {message.text}")
    try:
        workout_duration = int(message.text)
    except ValueError:
        await message.answer("Please enter the workout duration as a number in minutes.")
        return

    await state.update_data(workout_duration=workout_duration)
    await state.set_state(WorkoutLogging.commit_workout)
    await cmd_log_workout(message, CommandObject(prefix="/", command="log_workout"), state)


@router.message(Command("log_workout"))
async def cmd_log_workout(message: Message, command: CommandObject, state: FSMContext):
    logger.debug(f"command.args: {command.args}")
    
    state_data = await state.get_data()
    logger.debug(f"state_data: {state_data}")
    
    current_state = await state.get_state()
    if current_state != WorkoutLogging.commit_workout:
        if state_data.get('workout_type', None) is None:
            if command.args:
                if await validate_workout_type(message, command.args):
                    await state.update_data(workout_type=command.args)
                    await state.set_state(WorkoutLogging.waiting_for_workout_duration)
                    await message.answer("How many minutes did you workout?")
                return
            else:
                await state.set_state(WorkoutLogging.waiting_for_workout_type)
                await message.answer(
                    "Please specify the workout type.\n"
                    "Available types: " + ", ".join(WORKOUT_CALORIES.keys())
                )
            return
        if state_data.get('workout_duration', None) is None:
            await state.set_state(WorkoutLogging.waiting_for_workout_duration)
            await message.answer("How many minutes did you workout?")
            return
        return

    user_id = message.from_user.id
    stats = await users[user_id].get_current_stats()
    workout_type = state_data['workout_type']
    workout_duration = state_data['workout_duration']

    try:
        calories_burned = WORKOUT_CALORIES[workout_type] * workout_duration
        water_needed = (workout_duration // 30) * WATER_PER_WORKOUT  # 200ml of water every 30 minutes
        
        stats.burned_calories += calories_burned
        stats.workout_log.append({
            "type": workout_type,
            "duration": workout_duration,
            "calories": calories_burned,
            "timestamp": datetime.now().isoformat()
        })
        await state.clear()
        await message.answer(
            f"🏃‍♂️ {workout_type.capitalize()} {workout_duration} minutes\n"
            f"- Calories burned: {calories_burned} kcal\n"
            f"💧 Recommended water intake: {water_needed} ml of water"
        )
    except ValueError:
        await message.answer("Please enter the workout duration in minutes as a number.")
    except Exception as e:
        await message.answer("An error occurred while logging the workout.")


@router.message(Command("check_progress"))
async def cmd_check_progress(message: Message):
    user_id = message.from_user.id
    user = users[user_id]
    stats = await user.get_current_stats()
    
    # Update goals for the current day
    temp = await get_temperature(user.city, WEATHER_API_KEY)
    if temp is not None:
        await user.update_daily_goals(temp)
        
        # If the temperature changed significantly, give a recommendation
        if abs(temp - stats.temperature) > 5:
            temp_diff = "increased" if temp > stats.temperature else "decreased"
            await message.answer(
                f"🌡 Temperature {temp_diff}!\n"
                f"New recommendation for water intake: {stats.water_goal} ml"
            )
    
    await message.answer(
        "📊 Progress for today:\n"
        f"Water:\n"
        f"- Drunk: {stats.logged_water} ml out of {stats.water_goal} ml.\n"
        f"- Remaining: {max(0, stats.water_goal - stats.logged_water)} ml.\n\n"
        f"Calories:\n"
        f"- Consumed: {stats.logged_calories} kcal out of BMR = {stats.calorie_goal} kcal.\n"
        f"- Burned: {stats.burned_calories} kcal.\n"
        f"- Balance (consumed - BMR - burned): {stats.logged_calories - stats.calorie_goal - stats.burned_calories} kcal."
    )


@router.message(Command("charts"))
async def cmd_charts(message: Message):
    """Sends progress charts to the user"""
    user_id = message.from_user.id
    stats = await users[user_id].get_current_stats()

    try:
        # Generate chart
        buffer = await generate_progress_charts(stats)
        
        # Create object to send chart
        photo = BufferedInputFile(
            buffer.getvalue(),
            filename="progress_charts.png"
        )
        
        # Send chart with caption
        await message.answer_photo(
            photo,
            caption=(
                "📊 Your progress for today:\n"
                f"💧 Water: {stats.logged_water}/{stats.water_goal} ml\n"
                f"🔥 Calories: {stats.logged_calories}/{stats.calorie_goal} kcal\n"
                f"💪 Burned: {stats.burned_calories} kcal\n"
                f"💪 Balance (consumed - BMR - burned): {stats.logged_calories - stats.calorie_goal - stats.burned_calories} kcal."
            )
        )
    except Exception as e:
        print(f"Error generating charts: {e}")
        await message.answer("Sorry, an error occurred while generating charts.")

@router.message(Command("history"))
async def cmd_history(message: Message, state: FSMContext):
    """Shows the activity history of the user"""
    await state.set_state(HistoryPeriod.waiting_for_period)
    await message.answer(
        "For which period would you like to see the history?\n"
        "1 - Today\n"
        "7 - This week\n"
        "30 - This month\n"
        "Enter the number of days (1 to 30):"
    )

@router.message(HistoryPeriod.waiting_for_period)
async def process_history_period(message: Message, state: FSMContext):
    try:
        days = int(message.text)
        if not 1 <= days <= 30:
            raise ValueError("Period must be between 1 and 30 days")
            
        user_id = message.from_user.id
        user = users[user_id]
        
        # Get history for the specified period
        start_date = datetime.now().date() - timedelta(days=days)
        
        # Format report
        report = f"📊 Activity history for the last {days} days:\n\n"
        
        # Iterate through all days in the range
        for day_offset in range(days-1, -1, -1):
            date = (datetime.now().date() - timedelta(days=day_offset)).isoformat()
            if date in user.daily_stats:
                stats = user.daily_stats[date]
                day_str = datetime.fromisoformat(date).strftime("%d.%m")
                
                report += f"📅 {day_str}:\n"
                report += f"💧 Water: {stats.logged_water}/{stats.water_goal} ml\n"
                report += f"🔥 Calories: {stats.logged_calories}/{stats.calorie_goal} kcal\n"
                report += f"💪 Burned: {stats.burned_calories} kcal\n"
                
                if stats.food_log:
                    report += "🍽 Food:\n"
                    for log in stats.food_log:
                        time = datetime.fromisoformat(log['timestamp']).strftime("%H:%M")
                        report += f"- {time}: {log['name']} ({log['weight']}g, {log['calories']:.1f} kcal)\n"
                
                if stats.workout_log:
                    report += "🏃‍♂️ Workouts:\n"
                    for log in stats.workout_log:
                        time = datetime.fromisoformat(log['timestamp']).strftime("%H:%M")
                        report += f"- {time}: {log['type'].capitalize()} ({log['duration']} min, {log['calories']} kcal)\n"
                
                report += "\n"
        
        if not user.daily_stats:
            report += "No data for the specified period"
            
        # Send report
        await message.answer(report)
        await state.clear()
        
    except ValueError as e:
        await message.answer(str(e))
    except Exception as e:
        await message.answer("An error occurred while getting the history.")
        logger.error(f"Error in history: {e}")

# Start bot
async def main():
    try:
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher()
        dp.include_router(router)
        
        logger.info("Bot started!")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())
