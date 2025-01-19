# Fitness Bot for Telegram

A Telegram bot for health and fitness tracking, helping users monitor their water intake, calories, and physical activity.

## Key Features

- 💧 Water intake tracking
- 🍎 Calorie counting
- 🏃‍♂️ Exercise logging
- 📊 Progress visualization
- 🌡️ Weather conditions consideration for water intake calculation

## Technologies

- Python 3.8+
- aiogram 3.x (asynchronous framework for Telegram bots)
- aiohttp (for asynchronous HTTP requests)
- matplotlib (graph generation)
- python-dotenv (environment variables management)
- FatSecret API (food information)

## Project Structure

```
src/
├── bot.py # Main bot logic
├── config.py # Configuration and constants
├── models.py # Data models
└── utils.py # Helper functions
```

## Architecture

### Configuration (config.py)

The module is responsible for:
- Loading environment variables from `.env` file
- Setting up logging
- Defining calculation constants
- Verifying required API keys

### Middleware

The bot uses two middleware components:

1. **LoggingMiddleware** - for logging all messages
2. **CheckUserProfileMiddleware** - checks for user profile existence

### Finite State Machine (FSM)

Used to manage dialogues in two main scenarios:
- User profile setup (ProfileSetup)
- Food logging (FoodLogging)

### Main Commands

- `/start` - start working with the bot
- `/set_profile` - configure profile
- `/log_water` - record water intake
- `/log_food` - record food intake
- `/log_workout` - record workout
- `/check_progress` - check progress
- `/charts` - show progress charts

## Implementation Details

### Asynchronous Programming

The bot is built on asynchronous programming (async/await), which provides:
- Processing multiple requests simultaneously
- Efficient work with external APIs
- No blocking of the main thread

### Error Handling

An extensive error handling system is implemented through try/except blocks for:
- User input validation
- External API error handling
- Protection against incorrect data

### Data Visualization

The bot generates progress charts using matplotlib:
- Water intake chart
- Calorie chart (consumption/burning)

### Data Storage

In the current version, data is stored in memory (users dictionary). For production, it's recommended to use a database.

## Installation and Setup

1. Clone the repository:
```sh
git clone [repository URL]
```

2. Install dependencies:
```sh
pip install -r requirements.txt
```

3. Create a `.env` file and add the necessary environment variables:
```env
BOT_TOKEN=your_telegram_bot_token
WEATHER_API_KEY=your_weather_api_key
CONSUMER_KEY=your_fatsecret_consumer_key
CONSUMER_SECRET=your_fatsecret_consumer_secret
```

4. Start the bot:
```sh
python src/bot.py
```

## License

MIT License - see [LICENSE](LICENSE) file


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
