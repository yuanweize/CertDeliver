# Contributing to CertDeliver

First off, thanks for taking the time to contribute! 🎉

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title** describing the issue
- **Steps to reproduce** the behavior
- **Expected behavior** vs actual behavior
- **Environment details** (OS, Python version, etc.)
- **Logs** if applicable (sanitize any sensitive data)

### Suggesting Enhancements

Enhancement suggestions are welcome! Please include:

- **Use case** - Why is this enhancement needed?
- **Proposed solution** - How would you implement it?
- **Alternatives considered** - What other approaches did you consider?

### Pull Requests

1. **Fork** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following the code style
4. **Run tests** and ensure they pass:
   ```bash
   pip install -e ".[dev]"
   pytest
   ruff check src/
   mypy src/certdeliver
   ```
5. **Commit** with a clear message:
   ```bash
   git commit -m "feat: add amazing feature"
   ```
6. **Push** and open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/CertDeliver.git
cd CertDeliver

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/ tests/

# Run type checker
mypy src/certdeliver
```

## Code Style

- Follow [PEP 8](https://pep8.org/)
- Use type hints for all function parameters and return values
- Maximum line length: 88 characters (Black style)
- Write docstrings for public functions and classes

## Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

## Questions?

Feel free to open an issue with the `question` label.

---

Thank you for contributing! 🙏
