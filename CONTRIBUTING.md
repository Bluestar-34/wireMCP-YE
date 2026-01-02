# Contributing to WireMCP-YE

Thank you for your interest in contributing to WireMCP-YE! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/wireMCP-YE.git
   cd wireMCP-YE
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"  # Install with dev dependencies
   ```

4. **Install pre-commit hooks (optional but recommended)**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Code Style

We use the following tools for code quality:

- **Ruff** - Fast Python linter and formatter
- **MyPy** - Static type checking
- **Black** (via Ruff) - Code formatting

### Running Code Quality Checks

```bash
# Format code
ruff format wireshark_mcp.py

# Check linting
ruff check wireshark_mcp.py

# Type checking
mypy wireshark_mcp.py
```

## Testing

1. **Write tests** for new features
2. **Run tests** before submitting:
   ```bash
   pytest
   ```

3. **Check test coverage**:
   ```bash
   pytest --cov=wireshark_mcp --cov-report=html
   ```

## Commit Messages

Follow conventional commits format:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

Example:
```
feat: add threat detection with URLhaus integration
```

## Pull Request Process

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and commit them with clear messages

3. **Run tests and checks**:
   ```bash
   pytest
   ruff check wireshark_mcp.py
   mypy wireshark_mcp.py
   ```

4. **Push your branch** and create a Pull Request

5. **Ensure all CI checks pass**

## Adding New Tools

When adding a new Wireshark tool:

1. Add the method to the `WiresharkMCP` class
2. Register it in the `register_wireshark_tools` function
3. Add comprehensive docstrings
4. Add type hints
5. Add tests
6. Update the README.md

## Documentation

- Update README.md for user-facing changes
- Add docstrings to all public functions and classes
- Update UNIFICATION_SUMMARY.md if adding major features

## Questions?

Feel free to open an issue for questions or discussions.


