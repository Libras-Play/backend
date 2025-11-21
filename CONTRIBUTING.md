# Contributing to LibrasPlay

Thank you for your interest in contributing to LibrasPlay! 🎉

We welcome contributions from everyone, whether you're fixing bugs, adding features, improving documentation, or reporting issues.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)
- [Documentation](#documentation)
- [Getting Help](#getting-help)

---

## 📜 Code of Conduct

This project adheres to a [Code of Conduct](./CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to conduct@librasplay.com.

---

## 🚀 How to Contribute

### Reporting Bugs

Before creating a bug report, please:
1. **Check existing issues** to avoid duplicates
2. **Use the latest version** of the code
3. **Provide detailed information** about the bug

When reporting bugs, include:
- **Summary**: Clear, descriptive title
- **Steps to reproduce**: Numbered list of steps
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Environment**: OS, Python version, Docker version
- **Logs/Screenshots**: Any relevant error messages

**Example**:
```markdown
**Bug**: Lives not regenerating after 3 hours

**Steps**:
1. Create user with 0 lives
2. Wait 3 hours
3. Check lives count via GET /api/v1/lives

**Expected**: Lives should regenerate to 1
**Actual**: Lives remain at 0

**Environment**: 
- OS: Ubuntu 22.04
- Python: 3.11.6
- Docker: 24.0.7

**Logs**:
```
ERROR: Lives regeneration failed: division by zero
```
```

### Suggesting Features

We love new ideas! Before suggesting a feature:
1. **Check the roadmap** in README.md
2. **Search existing issues** to avoid duplicates
3. **Describe the problem** you're trying to solve

When suggesting features, include:
- **Problem statement**: What problem does this solve?
- **Proposed solution**: How would it work?
- **Alternatives**: Other approaches you considered
- **Use cases**: Real-world scenarios

### Questions

For questions about using LibrasPlay:
- **GitHub Discussions**: For general questions
- **Issues**: For potential bugs
- **Email**: team@librasplay.com for private inquiries

---

## 💻 Development Setup

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+
- Git 2.30+
- AWS CLI 2.0+ (for deployments)

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/librasplay-backend.git
cd librasplay-backend

# Add upstream remote
git remote add upstream https://github.com/librasplay/backend.git
```

### Local Development Setup

```bash
# 1. Copy environment templates
cp services/content-service/.env.template services/content-service/.env
cp services/user-service/.env.template services/user-service/.env
cp services/ml-service/.env.template services/ml-service/.env

# 2. Edit .env files with local values
# For local dev, use default values from templates

# 3. Start services
docker-compose up --build

# 4. Verify services are running
curl http://localhost:8001/content/health
curl http://localhost:8002/users/health
curl http://localhost:8003/ml/health
```

### Python Virtual Environment (Alternative)

```bash
# For development without Docker:
cd services/content-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies
```

---

## 📏 Coding Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

- **Line Length**: 100 characters (not 79)
- **Quotes**: Double quotes for strings
- **Imports**: Organized (stdlib, third-party, local)
- **Type Hints**: Required for all functions
- **Docstrings**: Google style

**Example**:
```python
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User


async def get_user_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Retrieve a user by their unique ID.

    Args:
        user_id: The unique identifier of the user.
        db: Database session dependency.

    Returns:
        User object if found, None otherwise.

    Raises:
        DatabaseError: If database query fails.
    """
    # Implementation here
    pass
```

### Code Formatting

We use automated formatters:

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Format code
black services/content-service/app/
isort services/content-service/app/

# Lint code
flake8 services/content-service/app/
pylint services/content-service/app/

# Type checking
mypy services/content-service/app/

# Security checks
bandit -r services/content-service/app/
```

### Configuration

See `.flake8`, `pyproject.toml`, `.isort.cfg` for tool configurations.

---

## 📝 Commit Guidelines

### Commit Message Format

We follow **Conventional Commits**:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, configs)
- `perf`: Performance improvements
- `ci`: CI/CD changes

**Scope** (optional): Service or component affected
- `content-service`
- `user-service`
- `ml-service`
- `infra`
- `docs`

**Examples**:
```
feat(user-service): add lives regeneration endpoint

Implements automatic lives regeneration every 3 hours.
- Add /api/v1/lives/regenerate endpoint
- Add scheduled task for regeneration
- Update DynamoDB schema

Closes #123

---

fix(content-service): resolve SQL injection in topics filter

Use parameterized queries to prevent SQL injection vulnerability.

BREAKING CHANGE: Topics filter API now requires JSON body instead of query params

---

docs(readme): update quick start guide

Add missing step for copying .env.template files
```

### Commit Best Practices

- ✅ **Atomic commits**: One logical change per commit
- ✅ **Clear messages**: Describe what and why, not how
- ✅ **Reference issues**: Use `Closes #123` or `Fixes #456`
- ✅ **Sign commits**: Use GPG signing for security
- ❌ **Avoid**: "fix", "update", "changes" without context

---

## 🔄 Pull Request Process

### Before Submitting

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/add-leaderboard
   ```

2. **Make your changes** following coding standards

3. **Write tests** for new functionality

4. **Run tests locally**:
   ```bash
   pytest tests/ -v --cov=app --cov-report=html
   ```

5. **Update documentation** if needed

6. **Commit changes** following commit guidelines

7. **Push to your fork**:
   ```bash
   git push origin feature/add-leaderboard
   ```

### Submitting a Pull Request

1. **Go to GitHub** and create a Pull Request from your fork

2. **Fill out the PR template**:
   - Description of changes
   - Related issues
   - Type of change (bugfix, feature, etc.)
   - Checklist completion

3. **Request review** from maintainers

4. **Wait for CI checks** to pass:
   - Tests
   - Linting
   - Security scans
   - Build

5. **Address review feedback**:
   - Make requested changes
   - Push additional commits
   - Respond to comments

6. **Squash commits** if requested (optional)

7. **Merge**: Maintainer will merge after approval

### PR Title Format

Use conventional commit format:
```
feat(user-service): add leaderboard endpoint
fix(content-service): resolve exercise duplication bug
docs(readme): update deployment instructions
```

### PR Checklist

Before submitting, ensure:
- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] No merge conflicts
- [ ] Commit messages follow guidelines
- [ ] No secrets or credentials in code
- [ ] Security scan passes
- [ ] Screenshots attached (if UI changes)

---

## 🧪 Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific service
cd services/content-service
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html

# Specific test file
pytest tests/test_lives.py -v

# Specific test function
pytest tests/test_lives.py::test_regenerate_lives -v
```

### Writing Tests

Use **pytest** with **fixtures**:

```python
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.fixture
async def client():
    """HTTP client fixture."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_user_lives(client: AsyncClient):
    """Test retrieving user lives."""
    response = await client.get("/api/v1/lives/test-user-id")
    assert response.status_code == 200
    data = response.json()
    assert "current_lives" in data
    assert data["current_lives"] >= 0
    assert data["max_lives"] == 5
```

### Test Coverage

We aim for **≥80% coverage** on all services:

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

Missing coverage will be highlighted in PR reviews.

---

## 📚 Documentation

### Code Documentation

- **Docstrings**: Required for all public functions/classes
- **Type hints**: Required for function signatures
- **Inline comments**: For complex logic only

### API Documentation

FastAPI auto-generates OpenAPI docs:
- Local: http://localhost:8001/content/docs
- Update route descriptions in FastAPI decorators

### README Updates

Update README.md when:
- Adding new services
- Changing setup instructions
- Adding new dependencies
- Changing deployment process

---

## 🆘 Getting Help

### Resources

- **Documentation**: Check `/docs` folder
- **GitHub Discussions**: Ask questions
- **Issues**: Search existing issues
- **Email**: team@librasplay.com

### Common Issues

**Issue**: `docker-compose up` fails with "port already in use"

**Solution**:
```bash
# Stop all containers
docker-compose down

# Find process using port
lsof -i :8001  # macOS/Linux
netstat -ano | findstr :8001  # Windows

# Kill process or change port in docker-compose.yml
```

**Issue**: Database migrations fail

**Solution**:
```bash
# Reset database
docker-compose down -v
docker-compose up --build

# Or run migrations manually
cd services/content-service
alembic upgrade head
```

---

## 🏆 Recognition

Contributors will be acknowledged in:
- **CONTRIBUTORS.md**: List of all contributors
- **Release notes**: Mentioned in relevant releases
- **GitHub**: Contributor badge on profile

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the [MIT License](./LICENSE).

---

## 🙏 Thank You!

Your contributions make LibrasPlay better for everyone. Thank you for taking the time to contribute! 🎉

---

**Questions about contributing?**  
Email: team@librasplay.com  
GitHub: https://github.com/librasplay/backend/discussions

**Last Updated**: 2025-11-20
