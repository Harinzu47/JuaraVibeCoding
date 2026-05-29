# Contributing to AturModal

Thank you for your interest in contributing to AturModal! This document outlines guidelines and standards to ensure a clean, maintainable, and high-quality codebase.

## Code of Conduct

Please be respectful, professional, and collaborative in all communication and pull requests.

## Workflow

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-awesome-feature`.
3. Set up the development environment (see below).
4. Implement your changes, ensuring you write appropriate tests.
5. Format and lint your code.
6. Commit changes following conventional commits: `git commit -m "feat: add secure rate limiting"`.
7. Push to your branch and open a Pull Request.

## Development Setup

1. Install Python 3.10+ and Node.js 18+.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
3. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```

## Code Quality Standards

We use `black` for formatting, `flake8` for linting, and `mypy` for static type checking.

Before submitting a PR, make sure your code passes all checks:

```bash
# Format Python code
black app/ tests/
isort app/ tests/

# Lint Python code
flake8 app/ tests/
mypy app/

# Run tests
pytest --cov=app
```

### Formatting Rules

*   **Python:** Indent with 4 spaces. Line length limit is 88 characters (Black standard).
*   **JS/React:** Indent with 2 spaces.
*   **Language:** Write all code, variable names, database schemas, docstrings, and comments in **English**.

## Pull Request Guidelines

*   Provide a clear, descriptive title.
*   Explain the problem you are solving and your approach.
*   Include links to relevant issues.
*   Ensure all tests pass and test coverage is maintained.
*   Keep PRs focused on a single logical change. Large PRs should be broken down.
