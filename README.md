# LibrasPlay - Sign Language Learning Platform

> 🤟 An interactive platform for learning sign language through AI-powered gesture recognition, gamification, and adaptive learning.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)

---

## 🎯 About

LibrasPlay is an open-source educational platform designed to make sign language learning accessible, engaging, and effective. Using modern web technologies, machine learning, and gamification principles, it provides an interactive learning experience for students of all levels.

## ✨ Features

- 🤖 **AI-Powered Recognition**: Machine learning models for gesture recognition and feedback
- 🎮 **Gamification**: XP system, achievements, streaks, and progress tracking
- 📚 **Structured Learning**: Organized lessons, topics, and difficulty progression
- 🌐 **Multi-language Support**: Platform supports multiple interface languages
- 📱 **Adaptive Learning**: Personalized exercise selection based on user performance
- 🏆 **Progress Tracking**: Detailed analytics of learning progress and achievements

## 🚀 Quick Start

### Using Docker (Recommended)

1. **Clone and setup**
   ```bash
   git clone https://github.com/your-org/libras-play-backend.git
   cd libras-play-backend
   
   # Copy environment templates
   cp services/content-service/.env.template services/content-service/.env
   cp services/user-service/.env.template services/user-service/.env
   cp services/ml-service/.env.template services/ml-service/.env
   ```

2. **Start all services**
   ```bash
   docker-compose up --build
   ```

3. **Access the APIs**
   - Content Service: http://localhost:8001/docs
   - User Service: http://localhost:8002/docs  
   - ML Service: http://localhost:8003/docs
   - Adaptive Service: http://localhost:8004/docs

## 🏗️ Architecture

LibrasPlay uses a microservices architecture with clear separation of concerns:

| Service | Purpose | Database | 
|---------|---------|----------|
| **content-service** | Educational content, lessons, exercises | PostgreSQL |
| **user-service** | User profiles, progress, gamification | DynamoDB |
| **ml-service** | AI/ML models for gesture recognition | S3 + Local storage |
| **adaptive-service** | Personalized learning algorithms | PostgreSQL |

### Core Features
- ✅ **Interactive Exercises**: Multiple exercise types (multiple choice, gesture recognition)
- ✅ **Progress System**: XP points, levels, and achievement badges
- ✅ **Adaptive Difficulty**: Dynamic difficulty adjustment based on performance
- ✅ **Multi-language Content**: Support for different sign languages and interface languages
- ✅ **Real-time Feedback**: Instant feedback on exercise performance

## 🛠️ Tech Stack

### Backend
- **Python 3.11** - Modern Python with async support
- **FastAPI** - High-performance web framework with automatic API docs
- **SQLAlchemy** - Object-relational mapping with async support
- **Alembic** - Database migration management
- **Docker & Docker Compose** - Containerization for easy deployment

### Databases
- **PostgreSQL** - Relational database for structured content
- **DynamoDB** - NoSQL database for user data and real-time features

### Machine Learning
- **TensorFlow/PyTorch** - ML frameworks for gesture recognition
- **OpenCV** - Computer vision processing
- **NumPy/Pandas** - Data processing and analysis

### DevOps & Deployment
- **Docker** - Containerization
- **GitHub Actions** - CI/CD automation
- **Terraform** - Infrastructure as Code (optional)
- **AWS** - Cloud deployment (optional, can run on any cloud)

## 📁 Project Structure

```
backend/
├── services/                    # Microservices
│   ├── content-service/         # Educational content management
│   │   ├── app/                 # FastAPI application
│   │   ├── alembic/             # Database migrations
│   │   ├── seed_data/           # Sample content data
│   │   └── tests/               # Unit and integration tests
│   ├── user-service/            # User management and progress
│   ├── ml-service/              # Machine learning and AI
│   └── adaptive-service/        # Adaptive learning algorithms
├── infra/                       # Infrastructure as Code
│   └── terraform/               # Cloud deployment configurations
├── scripts/                     # Utility scripts
├── docs/                        # Documentation
├── .github/workflows/           # CI/CD pipelines
├── docker-compose.yml           # Local development setup
├── README.md                    # This file
├── CONTRIBUTING.md              # How to contribute
└── LICENSE                      # MIT License
```

## 💻 Development

### Prerequisites
- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Python** 3.11+ (for local development)
- **Git** for version control

### Local Development Setup

#### Option 1: Docker (Recommended)
```bash
# Clone the repository
git clone https://github.com/your-org/libras-play-backend.git
cd libras-play-backend

# Copy environment templates
find . -name "*.env.template" -exec sh -c 'cp "$1" "${1%.template}"' _ {} \;

# Start all services
docker-compose up --build
```

#### Option 2: Native Python Development
```bash
# Content Service
cd services/content-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up database
export DATABASE_URL="postgresql://postgres:password@localhost:5432/libras_content"
alembic upgrade head

# Run service
uvicorn app.main:app --reload --port 8001
```

### Running Tests
```bash
# All services with Docker
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Individual service tests
cd services/content-service
pytest tests/ -v --cov=app

# With coverage report
pytest tests/ -v --cov=app --cov-report=html
```

### Database Management

#### Creating Migrations (Content Service)
```bash
cd services/content-service

# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new feature"

# Apply migrations
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

## 🚀 Deployment

### Docker Deployment
```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy with production configuration
docker-compose -f docker-compose.prod.yml up -d
```

### Cloud Deployment

The project includes infrastructure-as-code templates for easy cloud deployment:

- **AWS**: See `infra/terraform/` for Terraform configurations
- **Other Clouds**: The Docker setup can be deployed on any container platform

#### Environment Variables

Configure these environment variables for production:

```bash
# Database connections
DATABASE_URL=postgresql://user:pass@host:5432/dbname
DYNAMODB_REGION=us-east-1

# Security
JWT_SECRET_KEY=your-secure-secret-key
CORS_ORIGINS=https://yourdomain.com

# ML Service
ML_MODEL_PATH=/models/
MAX_FILE_SIZE=10485760
```

⚠️ **Security Note**: Never commit real credentials to the repository. Use environment variables or secret management services.

### CI/CD

The project includes GitHub Actions workflows for:
- Automated testing on pull requests
- Code quality checks and security scanning
- Docker image building and deployment

## 📖 API Documentation

Once the services are running, you can access the interactive API documentation:

- **Content Service**: http://localhost:8001/docs - Manage educational content, exercises, and topics
- **User Service**: http://localhost:8002/docs - Handle user profiles, progress, and achievements  
- **ML Service**: http://localhost:8003/docs - Process sign language recognition requests
- **Adaptive Service**: http://localhost:8004/docs - Adaptive learning algorithms and recommendations

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

### Getting Started
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/awesome-feature`)
3. Set up your development environment (see [Development](#-development))
4. Make your changes and add tests
5. Run the test suite to ensure everything works
6. Commit your changes (`git commit -m 'Add awesome feature'`)
7. Push to the branch (`git push origin feature/awesome-feature`)
8. Open a Pull Request

### Guidelines
- Write clear, descriptive commit messages
- Add tests for new features
- Update documentation when needed
- Follow the existing code style and conventions
- Be respectful and collaborative

For detailed guidelines, see [CONTRIBUTING.md](./CONTRIBUTING.md)

## 🔒 Security

Security is important to us. If you discover a security vulnerability, please:

1. **DO NOT** open a public GitHub issue
2. Email us at: [security@librasplay.com] (replace with actual contact)
3. Include details about the vulnerability
4. Allow time for us to address the issue before public disclosure

See [SECURITY.md](./SECURITY.md) for our full security policy.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## 🌟 Roadmap

- [ ] **Enhanced AI Models**: Improved gesture recognition accuracy
- [ ] **Mobile SDK**: React Native/Flutter integration
- [ ] **Social Features**: User communities and leaderboards  
- [ ] **Accessibility**: Screen reader support and keyboard navigation
- [ ] **Analytics Dashboard**: Learning progress insights for educators
- [ ] **Offline Mode**: Download lessons for offline practice
- [ ] **Multi-language Expansion**: Support for ASL, BSL, and other sign languages

## 💬 Community & Support

- 🐛 **Bug Reports**: [Open an issue](https://github.com/your-org/libras-play-backend/issues)
- 💡 **Feature Requests**: [Start a discussion](https://github.com/your-org/libras-play-backend/discussions)  
- 📚 **Documentation**: Check the `/docs` folder for detailed guides
- 💬 **Questions**: Use GitHub Discussions for general questions

---

**Made with ❤️ for the sign language learning community**

*LibrasPlay is committed to making sign language education accessible to everyone.*
