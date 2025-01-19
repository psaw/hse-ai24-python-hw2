# Fitness Bot for Telegram

A Telegram bot for health and fitness tracking, helping users monitor their water intake, calories, and physical activity.

## Demo

YouTube: https://youtu.be/H2nxUPJyS18

## Key Features

- 💧 Water intake tracking with smart recommendations based on:
  - User's weight
  - Activity level
  - Weather conditions
- 🍎 Calorie counting with:
  - Food logging
  - BMR calculation
  - Activity-based adjustments
- 🏃‍♂️ Exercise logging
- 📊 Progress visualization
- 🌡️ Weather integration for smart water intake recommendations

## Technologies

- Python 3.12+
- aiogram 3.x (asynchronous framework for Telegram bots)
- aiohttp (for asynchronous HTTP requests)
- matplotlib (graph generation)
- python-dotenv (environment variables management)
- FatSecret API (food information)
- OpenWeatherMap API (weather data)
- Docker & Docker Compose (containerization)

## Project Structure

```
.
├── src/
│   ├── bot.py      # Main bot logic and handlers
│   ├── config.py   # Configuration and constants
│   ├── models.py   # Data models (UserProfile, DailyStats)
│   └── utils.py    # Helper functions
├── .env            # Environment variables
├── .dockerignore
├── docker-compose.yml          # Local deployment
├── docker-compose.cloud.yml    # Cloud deployment
├── Dockerfile
├── deploy.sh       # Yandex.Cloud deployment script
└── README.md
```

## Architecture

### Data Models (models.py)

- **UserProfile**: Stores user information and preferences
  - Basic info (weight, height, age)
  - Activity level
  - Location for weather data
  - Daily statistics tracking

- **DailyStats**: Tracks daily progress
  - Water intake
  - Calorie intake and burning
  - Food and workout logs
  - Daily goals based on user profile and conditions

### Configuration (config.py)

- Environment variables management
- Logging setup
- Calculation constants
- API keys verification

### State Management

The bot uses Finite State Machine (FSM) for managing:
- User profile setup flow
- Food logging process
- Workout logging

### Main Commands

- `/start` - Initialize bot interaction
- `/set_profile` - Configure user profile
- `/log_water` - Record water intake
- `/log_food` - Log food consumption
- `/log_workout` - Record exercise
- `/check_progress` - View current progress
- `/charts` - Generate progress visualizations
- `/history` - View past logs

## Deployment Options

### Local Deployment

1. Clone the repository
2. Create `.env` file with required variables:
```env
BOT_TOKEN=your_telegram_bot_token
WEATHER_API_KEY=your_weather_api_key
CONSUMER_KEY=your_fatsecret_consumer_key
CONSUMER_SECRET=your_fatsecret_consumer_secret
LOG_LEVEL=DEBUG
```

3. Run with Docker Compose:
```bash
docker-compose up --build .
```

### Cloud Deployment (Yandex.Cloud)

The project includes automated deployment to Yandex.Cloud:

1. Configure cloud environment variables in `.docker-compose.cloud.yml`

2. Use deployment script:
```bash
# Deploy or update
./deploy.sh

# Stop instance
./deploy.sh --stop

# Reset and redeploy
./deploy.sh --reset
```

#### Cloud Infrastructure

- Platform: Yandex.Cloud
- Container Registry (private): cr.yandex
- VM Configuration:
  - Platform: standard-v3
  - CPU: 2 cores
  - RAM: 4GB
  - Storage: 30GB
  - Region: ru-central1-a

## Error Handling

- Comprehensive error handling for API interactions
- Graceful degradation for weather service failures
- Input validation and sanitization
- Logging for debugging and monitoring

## Data Storage

Currently uses in-memory storage with the following structure:
- User profiles stored in memory dictionary
- Daily statistics tracked per user
- Persistent storage planned for production use

## License

MIT License - see [LICENSE](LICENSE) file
