import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, types, BaseMiddleware
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


from config import BOT_TOKEN, WEATHER_API_KEY, WORKOUT_CALORIES, logger
from models import UserProfile
from utils import get_temperature, get_food_info, generate_progress_charts, get_food_info_from_fs
from datetime import datetime


# Состояния FSM для настройки профиля
class ProfileSetup(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()

# Состояния для логирования еды
class FoodLogging(StatesGroup):
    waiting_for_weight = State()

# Хранилище данных пользователей
users: dict[int, UserProfile] = {}

router = Router()


# Middleware для проверки наличия профиля пользователя
class CheckUserProfileMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        user_id = event.from_user.id
        
        # Список разрешенных команд без профиля
        allowed_commands = ['/set_profile', '/start', '/help']
        
        # Пропускаем разрешенные команды и состояния заполнения профиля
        if ((event.text and any(event.text.startswith(cmd) for cmd in allowed_commands)) or 
            isinstance(data.get('state'), ProfileSetup) or
            data.get('raw_state') is not None and data['raw_state'].startswith('ProfileSetup')):
            return await handler(event, data)
            
        # Проверяем наличие профиля
        if user_id not in users:
            await event.answer("Сначала настройте профиль с помощью /set_profile")
            return
            
        return await handler(event, data)


# Middleware для логирования
class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        logger.info(f"Сообщение от {event.from_user.id}: {event.text}")
        return await handler(event, data)

# Регистрируем middleware
router.message.middleware(LoggingMiddleware())
router.message.middleware(CheckUserProfileMiddleware()) 

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я помогу вам отслеживать потребление воды и калорий.\n"
        "Используйте следующие команды:\n"
        "/set_profile - настроить профиль\n"
        "/log_water <мл> - записать выпитую воду\n"
        "/log_food <продукт> - записать съеденный продукт\n"
        "/log_workout <тип> <минуты> - записать тренировку\n"
        "/check_progress - проверить прогресс\n"
        "/charts - показать графики прогресса 📊"
    )
    
@router.message(Command("set_profile"))
async def cmd_set_profile(message: Message, state: FSMContext):
    await state.set_state(ProfileSetup.weight)
    await message.answer("Введите ваш вес (в кг):")

@router.message(ProfileSetup.weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
        await state.update_data(weight=weight)
        await state.set_state(ProfileSetup.height)
        await message.answer("Введите ваш рост (в см):")
    except ValueError:
        await message.answer("Пожалуйста, введите число. Попробуйте снова:")

@router.message(ProfileSetup.height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = float(message.text)
        await state.update_data(height=height)
        await state.set_state(ProfileSetup.age)
        await message.answer("Введите ваш возраст:")
    except ValueError:
        await message.answer("Пожалуйста, введите число. Попробуйте снова:")

@router.message(ProfileSetup.age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        await state.update_data(age=age)
        await state.set_state(ProfileSetup.activity)
        await message.answer("Сколько минут активности у вас в день?")
    except ValueError:
        await message.answer("Пожалуйста, введите целое число. Попробуйте снова:")
    
@router.message(ProfileSetup.activity)
async def process_activity(message: Message, state: FSMContext):
    try:
        activity = int(message.text)
        await state.update_data(activity=activity)
        await state.set_state(ProfileSetup.city)
        await message.answer("В каком городе вы находитесь?")
    except ValueError:
        await message.answer("Пожалуйста, введите целое число минут. Попробуйте снова:")
    
@router.message(ProfileSetup.city)
async def process_city(message: Message, state: FSMContext):
    city = message.text
    user_data = await state.get_data()
    user_id = message.from_user.id
    
    # Создаем профиль пользователя
    profile = UserProfile(
        user_id=user_id,
        weight=user_data['weight'],
        height=user_data['height'],
        age=user_data['age'],
        activity_minutes=user_data['activity'],
        city=city
    )

    try:
        # Получаем температуру для расчета нормы воды
        temp = await get_temperature(city, WEATHER_API_KEY)
        if temp is None:
            raise ValueError("Не удалось получить температуру")

        profile.water_goal = profile.calculate_water_goal(temp)
        profile.calorie_goal = profile.calculate_calorie_goal()
        users[user_id] = profile
        
        await state.clear()  # Очищаем состояние
        logger.info(f"Профиль настроен для пользователя {user_id}")
        await message.answer(
            "✅ Профиль настроен!\n"
            f"💧 Норма воды: {profile.water_goal:.0f} мл\n"
            f"🔥 Норма калорий: {profile.calorie_goal:.0f} ккал\n\n"
            "Используйте следующие команды:\n"
            "/log_water <мл> - записать выпитую воду\n"
            "/log_food <продукт> - записать съеденный продукт\n"
            "/log_workout <тип> <минуты> - записать тренировку\n"
            "/check_progress - проверить прогресс\n"
            "/charts - показать графики прогресса 📊"
        )
    except Exception as e:
        await message.answer(
            "❌ Не удалось получить данные о погоде.\n"
            "Пожалуйста, проверьте название города и попробуйте снова.\n"
            "Например: Moscow, London, New York"
        )

@router.message(Command("log_water"))
async def cmd_log_water(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Пожалуйста, укажите количество воды в мл. Например: /log_water 250")
        return

    user_id = message.from_user.id
 
    try:
        water_amount = float(command.args)
        users[user_id].logged_water += water_amount
        remaining = users[user_id].water_goal - users[user_id].logged_water
        await message.answer(
            f"✅ Записано: {water_amount} мл воды\n"
            f"💧 Осталось выпить: {max(0, remaining)} мл"
        )
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число.")

@router.message(Command("log_food"))
async def cmd_log_food(message: Message, command: CommandObject, state: FSMContext):
    if not command.args:
        await message.answer(
            "Пожалуйста, укажите название продукта.\n"
            "Например: /log_food банан"
        )
        return

    user_id = message.from_user.id

    # обращение к OpenFoodFacts
    # food_info = await get_food_info(command.args)

    # обращение к FatSecret
    food_info = await get_food_info_from_fs(command.args)


    if not food_info:
        logger.error("Не нашли продукт: {}".format(command.args))
        await message.answer(
            "Извините, не удалось найти информацию о продукте.\n"
            "Попробуйте другой продукт или проверьте написание."
        )
        return
    if food_info.get("error"):
        if food_info.get("suggest"):
            await message.answer(
                f"Ошибка при получении информации о продукте: {food_info['name']}\n"
                f"Попробуйте другой продукт или проверьте написание.\n"
                f"*Внимание*: {food_info['suggest']}"
            )
        else:
            await message.answer(
                f"Ошибка при получении информации о продукте: {food_info['name']}\n"
                "Попробуйте другой продукт или проверьте написание."
            )
        return
    try:
        await state.update_data(
            food_name=food_info["name"],
            calories_per_100=float(food_info["calories"])
        )
        await state.set_state(FoodLogging.waiting_for_weight)
        await message.answer(
            f"🍎 {food_info['name']}\n"
            f"Калорийность: {food_info['calories']:.1f} ккал/100г\n"
            "Сколько грамм вы съели?"
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке информации о продукте: {e}")
        await message.answer(
            "Произошла ошибка при обработке информации о продукте.\n"
            "Пожалуйста, попробуйте другой продукт."
        )

@router.message(Command("check_progress"))
async def cmd_check_progress(message: Message):
    user_id = message.from_user.id
    user = users[user_id]
    await message.answer(
        "📊 Прогресс:\n"
        f"Вода:\n"
        f"- Выпито: {user.logged_water} мл из {user.water_goal} мл.\n"
        f"- Осталось: {max(0, user.water_goal - user.logged_water)} мл.\n\n"
        f"Калории:\n"
        f"- Потреблено: {user.logged_calories} ккал из {user.calorie_goal} ккал.\n"
        f"- Сожжено: {user.burned_calories} ккал.\n"
        f"- Баланс: {user.logged_calories - user.burned_calories} ккал."
    )

@router.message(Command("log_workout"))
async def cmd_log_workout(message: Message, command: CommandObject):
    if not command.args:
        await message.answer(
            "Пожалуйста, укажите тип тренировки и время в минутах.\n"
            "Например: /log_workout бег 30\n"
            "Доступные типы: бег, ходьба, плавание, велосипед, йога, силовая"
        )
        return

    user_id = message.from_user.id

    try:
        workout_type, duration = command.args.split()
        duration = int(duration)
        
        if workout_type not in WORKOUT_CALORIES:
            await message.answer("Неизвестный тип тренировки. Используйте один из: бег, ходьба, плавание, велосипед, йога, силовая")
            return
            
        calories_burned = WORKOUT_CALORIES[workout_type] * duration
        water_needed = (duration // 30) * 200  # 200мл воды каждые 30 минут
        
        users[user_id].burned_calories += calories_burned
        users[user_id].workout_log.append({
            "type": workout_type,
            "duration": duration,
            "calories": calories_burned,
            "timestamp": datetime.now().isoformat()
        })
        
        await message.answer(
            f"🏃‍♂️ {workout_type.capitalize()} {duration} минут\n"
            f"- Сожжено калорий: {calories_burned} ккал\n"
            f"💧 Рекомендуется выпить: {water_needed} мл воды"
        )
    except ValueError:
        await message.answer("Пожалуйста, укажите время тренировки в минутах числом.")
    except Exception as e:
        await message.answer("Произошла ошибка при записи тренировки.")

@router.message(FoodLogging.waiting_for_weight)
async def process_food_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
        food_data = await state.get_data()
        calories = food_data['calories_per_100'] * weight / 100
        
        user_id = message.from_user.id
        users[user_id].logged_calories += calories
        users[user_id].food_log.append({
            "name": food_data['food_name'],
            "weight": weight,
            "calories": calories,
            "timestamp": datetime.now().isoformat()
        })
        
        await state.clear()
        await message.answer(
            f"✅ Записано: {food_data['food_name']}\n"
            f"- Вес: {weight} г\n"
            f"- Калории: {calories:.1f} ккал"
        )
    except ValueError:
        await message.answer("Пожалуйста, введите вес в граммах числом.")

@router.message(Command("charts"))
async def cmd_charts(message: Message):
    """Отправляет графики прогресса пользователю"""
    user_id = message.from_user.id

    try:
        # Генерируем график
        buffer = await generate_progress_charts(users[user_id])
        
        # Создаем объект для отправки графика
        photo = BufferedInputFile(
            buffer.getvalue(),
            filename="progress_charts.png"
        )
        
        # Отправляем график с подписью
        await message.answer_photo(
            photo,
            caption=(
                "📊 Ваш прогресс на сегодня:\n"
                f"💧 Вода: {users[user_id].logged_water}/{users[user_id].water_goal} мл\n"
                f"🔥 Калории: {users[user_id].logged_calories}/{users[user_id].calorie_goal} ккал\n"
                f"💪 Сожжено: {users[user_id].burned_calories} ккал"
            )
        )
    except Exception as e:
        print(f"Error generating charts: {e}")
        await message.answer("Извините, произошла ошибка при создании графиков.")

# Запуск бота
async def main():
    try:
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher()
        dp.include_router(router)
        
        logger.info("Бот запущен!")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    asyncio.run(main())
