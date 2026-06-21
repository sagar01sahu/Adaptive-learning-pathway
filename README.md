# 🎓 Adaptive Learning Platform

An AI-powered adaptive learning platform for computer science students that personalizes content difficulty and learning paths using reinforcement learning and NVIDIA API integration.

## ✨ Features

- **🤖 AI-Powered Content Generation**: Uses NVIDIA API to generate personalized learning materials
- **🧠 Reinforcement Learning Engine**: Adapts content difficulty based on user performance
- **🎯 Personalized Learning Paths**: Customized tracks for Software Engineers, Data Scientists, and Data Engineers
- **📊 Progress Tracking**: Visual progress bars, analytics, and performance metrics
- **🏆 Gamification**: Achievement badges and streak tracking
- **📱 Responsive Design**: Modern, mobile-friendly interface with TailwindCSS
- **🔐 Secure Authentication**: User registration and login system

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL (or SQLite for development)
- NVIDIA API key (included in project)

### Installation

1. **Clone and navigate to the project**
   ```bash
   cd adaptive-learning-platform
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your database URL if needed
   ```

5. **Initialize database**
   ```bash
   python init_db.py
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the platform**
   - Open http://localhost:5000
   - Login with demo account: `student@demo.com` / `demo123`

## 🏗️ Architecture

### Backend Components

- **Flask Application** (`app.py`): Main web server with API endpoints
- **Database Models** (`models.py`): SQLAlchemy models for users, progress, content
- **NVIDIA API Integration** (`nvidia_api.py`): Content generation using AI
- **Reinforcement Learning Engine** (`reinforcement_learning.py`): Adaptive difficulty system

### Frontend Components

- **Responsive Templates**: HTML5 with TailwindCSS styling
- **Interactive JavaScript**: Dynamic content loading and quiz functionality
- **Progressive Web App**: Modern UX with toast notifications

### Database Schema

```sql
-- Core tables
users: User profiles and authentication
learning_paths: Curriculum modules for each role/level
progress: User progress and RL state
content: AI-generated learning materials
quiz_results: Performance tracking
badges: Gamification achievements
```

## 🎮 User Flow

1. **Registration/Login**: Secure user authentication
2. **Role Selection**: Choose career focus (Software Engineer, Data Scientist, Data Engineer)
3. **Initial Assessment**: Quiz to determine skill level (Beginner, Intermediate, Pro)
4. **Personalized Dashboard**: View learning path and progress
5. **Module Learning**: AI-generated content adapted to user's performance
6. **Quizzes**: Test knowledge and unlock next modules
7. **Adaptive Progression**: RL engine adjusts difficulty based on performance

## 🧠 Reinforcement Learning System

The platform uses a sophisticated RL engine that:

- **Tracks Performance**: Monitors quiz scores, time taken, consistency
- **Adjusts Difficulty**: Dynamically changes content complexity (Levels 1-3)
- **Personalizes Content**: Generates hints and focus areas based on weak points
- **Optimizes Learning**: Balances challenge and success for optimal engagement

### RL Algorithm

```python
# Difficulty adjustment based on multiple factors
if score < 60%: decrease_difficulty()
elif score > 80%: increase_difficulty()

# Additional factors: consistency, trends, time_taken
# Exploration: occasionally try different difficulties
```

## 🎯 Learning Paths

### Software Engineer Track
- **Beginner**: HTML → CSS → JavaScript → Python → Git → Portfolio Project
- **Intermediate**: React → APIs → Databases → Backend → Auth → Full-Stack App
- **Pro**: System Design → Cloud → Microservices → Security → CI/CD → Capstone

### Data Scientist Track
- **Beginner**: Python → NumPy → Pandas → Visualization → Data Project
- **Intermediate**: Statistics → ML → Feature Engineering → Pipelines → Predictive Model
- **Pro**: Deep Learning → NLP → RL → Big Data → MLOps → AI Application

### Data Engineer Track
- **Beginner**: Python → SQL → ETL → Data Warehousing → Pipeline Project
- **Intermediate**: Advanced SQL → Spark → Data Lakes → Streaming → Pipeline Project
- **Pro**: Scalable Architecture → Security → Cloud Data → Real-time Analytics → Enterprise Infrastructure

## 🔧 Configuration

### Environment Variables

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Database
DATABASE_URL=postgresql://username:password@localhost/adaptive_learning

# NVIDIA API
NVIDIA_API_KEY=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
NVIDIA_API_URL=https://integrate.api.nvidia.com/v1/chat/completions
```

### Database Setup

For PostgreSQL:
```bash
# Install PostgreSQL
brew install postgresql  # macOS
sudo apt-get install postgresql  # Ubuntu

# Create database
createdb adaptive_learning
```

For SQLite (development):
```bash
# Just update DATABASE_URL in .env
DATABASE_URL=sqlite:///adaptive_learning.db
```

## 📊 API Endpoints

### Authentication
- `POST /signup` - User registration
- `POST /login` - User login
- `GET /logout` - User logout

### Learning
- `GET /dashboard` - User dashboard
- `POST /role-selection` - Set user role
- `POST /initial-quiz` - Submit initial assessment
- `GET /module/<id>` - View module content
- `POST /get-content` - Generate AI content
- `POST /submit-test` - Submit quiz answers
- `GET /progress` - Get user progress

## 🎨 Customization

### Adding New Roles

1. Update learning paths in `init_db.py`
2. Add role-specific quiz questions in `app.py`
3. Update role selection UI in `role_selection.html`

### Modifying RL Algorithm

Edit `reinforcement_learning.py`:
- Adjust performance thresholds
- Modify difficulty calculation logic
- Add new performance metrics

### Styling Changes

The platform uses TailwindCSS. Modify templates in `templates/` directory:
- Update color scheme in `base.html`
- Customize components in individual templates
- Add new UI elements as needed

## 🧪 Testing

### Manual Testing
1. Use demo account: `student@demo.com` / `demo123`
2. Complete initial quiz with different scores to test RL
3. Progress through modules to test unlocking system

### Performance Testing
- Monitor RL adaptation with different user behaviors
- Test NVIDIA API integration with various content types
- Verify database performance with multiple users

## 🚀 Deployment

### Local Development
```bash
python app.py  # Runs on http://localhost:5000
```

### Production Deployment

1. **Set production environment variables**
2. **Use production database** (PostgreSQL recommended)
3. **Configure web server** (Gunicorn + Nginx)
4. **Set up SSL certificate**
5. **Monitor logs and performance**

Example production setup:
```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and test thoroughly
4. Submit pull request with detailed description

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

**Database Connection Error**
- Check DATABASE_URL in .env
- Ensure PostgreSQL is running
- Verify database exists

**NVIDIA API Error**
- Check API key in .env
- Verify internet connection
- Platform falls back to generated content

**Module Not Unlocking**
- Check quiz passing score (>= 60%)
- Verify progress table updates
- Check current_progress field

**JavaScript Errors**
- Check browser console for errors
- Ensure all templates load correctly
- Verify API endpoints are responding

### Getting Help

- Check the logs in terminal
- Review browser developer tools
- Ensure all dependencies are installed
- Verify environment variables are set

## 🎯 Future Enhancements

- **Mobile App**: React Native or Flutter app
- **Advanced Analytics**: Detailed learning analytics dashboard
- **Social Features**: Study groups and peer learning
- **Content Marketplace**: User-generated learning materials
- **Integration**: LMS integration and API for external platforms
- **Advanced AI**: More sophisticated content generation and personalization
