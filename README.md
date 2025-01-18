# Фитнес-бот для Telegram

Telegram-бот для отслеживания здоровья и фитнеса, помогающий пользователям следить за потреблением воды, калорий и физической активностью.

## Основные возможности

- 💧 Отслеживание потребления воды
- 🍎 Подсчет калорий
- 🏃‍♂️ Запись физических упражнений
- 📊 Визуализация прогресса
- 🌡️ Учет погодных условий при расчете нормы воды

## Технологии

- Python 3.8+
- aiogram 3.x (асинхронный фреймворк для Telegram ботов)
- aiohttp (для асинхронных HTTP-запросов)
- matplotlib (генерация графиков)
- python-dotenv (управление переменными окружения)
- FatSecret API (информация о продуктах питания)

## Структура проекта

```
src/
├── bot.py # Основная логика бота
├── config.py # Конфигурация и константы
├── models.py # Модели данных
└── utils.py # Вспомогательные функции
```


## Архитектура

### Конфигурация (config.py)

Модуль отвечает за:
- Загрузку переменных окружения из `.env` файла
- Настройку логирования
- Определение констант для расчетов
- Проверку наличия необходимых API ключей

### Middleware

Бот использует два middleware:

1. **LoggingMiddleware** - для логирования всех сообщений
2. **CheckUserProfileMiddleware** - проверяет наличие профиля пользователя

### Конечный автомат (FSM)

Используется для управления диалогами в двух основных сценариях:
- Настройка профиля пользователя (ProfileSetup)
- Логирование приема пищи (FoodLogging)

### Основные команды

- `/start` - начало работы
- `/set_profile` - настройка профиля
- `/log_water` - запись потребления воды
- `/log_food` - запись приема пищи
- `/log_workout` - запись тренировки
- `/check_progress` - проверка прогресса
- `/charts` - показ графиков прогресса

## Особенности реализации

### Асинхронное программирование

Бот построен на асинхронном программировании (async/await), что обеспечивает:
- Обработку множества запросов одновременно
- Эффективную работу с внешними API
- Отсутствие блокировки основного потока

### Обработка ошибок

Реализована обширная система обработки ошибок через try/except блоки для:
- Валидации пользовательского ввода
- Обработки ошибок внешних API
- Защиты от некорректных данных

### Визуализация данных

Бот генерирует графики прогресса с помощью matplotlib:
- График потребления воды
- График калорий (потребление/сжигание)

### Хранение данных

В текущей версии данные хранятся в памяти (словарь users). В продакшн-версии рекомендуется использовать базу данных.

## Установка и запуск

1. Клонируйте репозиторий:
```sh
bash
git clone [URL репозитория]
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` и добавьте необходимые переменные окружения:
```env
BOT_TOKEN=your_telegram_bot_token
WEATHER_API_KEY=your_weather_api_key
CONSUMER_KEY=your_fatsecret_consumer_key
CONSUMER_SECRET=your_fatsecret_consumer_secret
```

4. Запустите бота:
```bash
python src/bot.py
```

## Лицензия

MIT License - см. файл [LICENSE](LICENSE)


# Deployment

1. Make sure all files are in the correct structure:
```sh
.
├── src/
│ ├── bot.py
│ ├── config.py
│ ├── models.py
│ └── utils.py
├── .env
├── .dockerignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

2. Create your `.env` file with the required environment variables:
```env
BOT_TOKEN=your_telegram_bot_token
WEATHER_API_KEY=your_weather_api_key
CONSUMER_KEY=your_fatsecret_consumer_key
CONSUMER_SECRET=your_fatsecret_consumer_secret
LOG_LEVEL=INFO
```

## Docker Deployment

### Running with Docker Compose:
1. Build and run with Docker Compose:
```bash
docker-compose up --build -d
```

2. View logs:
```bash
docker-compose logs -f
```

3. Stop the bot:
```bash
docker-compose down
```

### Running without Docker Compose:

1. Build the image:
```bash
docker build -t fitness-bot .
```

2. Run the container:
```bash
docker run -d --name fitness_bot --restart unless-stopped fitness-bot
```
