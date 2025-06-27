# Contributing to Brum Brum Tracker

Thank you for your interest in contributing to Brum Brum Tracker! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

This project is designed to be welcoming and inclusive. Please:

- Be respectful and constructive in all communications
- Help create a positive environment for everyone
- Focus on what is best for the community and project

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Node.js 14 or higher
- Git

### Setting Up Your Development Environment

1. Fork the repository on GitHub

2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/brum-brum-tracker.git
   cd brum-brum-tracker
   ```

3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-test.txt  # For testing
   ```

5. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your HOME_LAT, HOME_LON, and OpenSky API credentials
   ```

6. Run the development servers:
   ```bash
   # Backend WebSocket server
   python backend/app.py

   # Frontend HTTP server
   python serve.py
   ```

## Development Process

### Branch Naming Convention

- `feature/` - New features (e.g., `feature/add-flight-history`)
- `fix/` - Bug fixes (e.g., `fix/websocket-reconnection`)
- `docs/` - Documentation updates (e.g., `docs/update-api-docs`)
- `refactor/` - Code refactoring (e.g., `refactor/modularize-frontend`)
- `test/` - Test additions or fixes (e.g., `test/add-aircraft-service-tests`)

### Workflow

1. Create a new branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes, following the code style guidelines

3. Write or update tests for your changes

4. Run tests to ensure everything passes:
   ```bash
   python run_tests.py
   ```

5. Commit your changes with a descriptive message:
   ```bash
   git commit -m "Add feature: brief description of changes"
   ```

6. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

7. Create a pull request on GitHub

## Code Style Guidelines

### Python Code Style

- Follow PEP 8 guidelines
- Use type hints for function parameters and return values
- Maximum line length: 88 characters (Black formatter default)
- Use descriptive variable and function names
- Add docstrings to all functions and classes

Example:
```python
def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate bearing between two geographic points.
    
    Args:
        lat1: Latitude of the first point in degrees
        lon1: Longitude of the first point in degrees
        lat2: Latitude of the second point in degrees
        lon2: Longitude of the second point in degrees
        
    Returns:
        Bearing in degrees (0-360)
    """
    # Implementation here
```

### JavaScript Code Style

- Use ES6+ features (const/let, arrow functions, modules)
- Add JSDoc comments for functions
- Use camelCase for variables and functions
- Use PascalCase for classes
- Prefer async/await over callbacks

Example:
```javascript
/**
 * Connect to WebSocket server with automatic reconnection
 * @param {string} url - WebSocket server URL
 * @returns {Promise<WebSocket>} Connected WebSocket instance
 */
async function connectWebSocket(url) {
    // Implementation here
}
```

### General Guidelines

- Keep functions small and focused (single responsibility)
- Avoid magic numbers - use named constants
- Handle errors appropriately
- Log important events and errors
- Remove debug console.log statements before submitting

## Testing

### Running Tests

Run all tests:
```bash
python run_tests.py
```

Run specific test categories:
```bash
# Backend unit tests
pytest tests/unit/backend/

# Frontend tests
npm test

# Integration tests
pytest tests/integration/
```

### Writing Tests

- Write tests for all new functionality
- Aim for at least 80% code coverage
- Test both success and error cases
- Use descriptive test names

Example test:
```python
def test_calculate_bearing_north():
    """Test bearing calculation for due north direction."""
    bearing = calculate_bearing(0, 0, 1, 0)
    assert bearing == 0
```

## Submitting Changes

### Pull Request Guidelines

1. **Title**: Use a clear, descriptive title
   - Good: "Add WebSocket reconnection with exponential backoff"
   - Bad: "Fix bug"

2. **Description**: Include:
   - What changes were made and why
   - Any breaking changes
   - Related issue numbers (e.g., "Fixes #123")
   - Screenshots for UI changes

3. **Checklist**:
   - [ ] Tests pass locally
   - [ ] Code follows style guidelines
   - [ ] Documentation updated if needed
   - [ ] No console.log statements left in code
   - [ ] Commit messages are descriptive

### Code Review Process

- All submissions require review before merging
- Address reviewer feedback promptly
- Be open to suggestions and constructive criticism
- Update your PR based on feedback

## Reporting Issues

### Bug Reports

When reporting bugs, include:

1. **Environment**:
   - Operating system
   - Browser version
   - Python version
   - Node.js version

2. **Steps to reproduce**:
   - Detailed steps to reproduce the issue
   - Expected behavior
   - Actual behavior

3. **Additional context**:
   - Error messages
   - Console logs
   - Screenshots if applicable

### Feature Requests

For feature requests, describe:

1. **Use case**: Why is this feature needed?
2. **Proposed solution**: How might it work?
3. **Alternatives considered**: Other approaches you've thought about

## Questions?

If you have questions about contributing:

1. Check existing issues and pull requests
2. Review the documentation
3. Create a new issue with the "question" label

Thank you for contributing to Brum Brum Tracker!