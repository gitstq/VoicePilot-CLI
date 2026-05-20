# Contributing to VoicePilot-CLI

Thank you for your interest in contributing to VoicePilot-CLI! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- git

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/voicepilot-cli/voicepilot-cli.git
   cd voicepilot-cli
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or
   .venv\Scripts\activate     # Windows
   ```

3. Install in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

4. Install optional dependencies as needed:
   ```bash
   pip install -e ".[openai,tts-edge,tui]"
   ```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_agent.py -v
```

### Code Quality

```bash
# Lint with ruff
make lint

# Type check with mypy
make typecheck

# Format code
make format
```

## Project Structure

```
voicepilot_cli/
├── __init__.py          # Package init
├── __main__.py          # Entry point (python -m voicepilot_cli)
├── cli.py               # CLI argument parser
├── config.py            # Configuration management
├── agent/               # Agent core logic
├── voice/               # STT/TTS engines
├── llm/                 # LLM backends
├── plugins/             # Plugin system
├── tui/                 # Terminal UI
└── utils/               # Utilities
```

## Design Principles

1. **Zero Core Dependencies**: The core functionality uses only Python stdlib. All external packages are optional.
2. **Graceful Degradation**: If an optional dependency is not installed, the feature is disabled with a clear message.
3. **Plugin Architecture**: Extend functionality through plugins without modifying core code.
4. **Type Safety**: Use type hints throughout the codebase.
5. **Clear Documentation**: Every module, class, and public function must have docstrings.

## Coding Standards

- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Write docstrings in Google style format
- Keep functions focused and small (single responsibility)
- Use descriptive variable names
- Add comments for complex logic

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

feat(agent): add streaming response support
fix(tts): handle edge-tts connection timeout
docs: update configuration guide
refactor(llm): simplify backend interface
test(plugins): add calculator plugin tests
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests and linting: `make test && make lint`
5. Commit with conventional commit messages
6. Push to your fork: `git push origin feature/my-feature`
7. Open a Pull Request

## Reporting Issues

When reporting issues, please include:

- Python version
- Operating system
- Installed dependencies (`pip freeze`)
- Steps to reproduce
- Expected vs actual behavior
- Relevant log output

## Adding a New Plugin

1. Create a new file in `voicepilot_cli/plugins/`
2. Inherit from `PluginBase` class
3. Implement required methods: `name()`, `description()`, `execute()`
4. Register in the plugin registry
5. Add tests in `tests/`

Example:

```python
from voicepilot_cli.plugins.base import PluginBase

class MyPlugin(PluginBase):
    @property
    def name(self) -> str:
        return "my_plugin"

    @property
    def description(self) -> str:
        return "My custom plugin"

    def execute(self, command: str, **kwargs) -> str:
        # Plugin logic here
        return "Result"
```

## Adding a New LLM Backend

1. Create a new file in `voicepilot_cli/llm/`
2. Inherit from `LLMBackendBase` class
3. Implement required methods: `generate()`, `stream()`
4. Register in the LLM backend factory
5. Add optional dependency to `setup.py` and `pyproject.toml`

## License

By contributing to VoicePilot-CLI, you agree that your contributions will be licensed under the MIT License.
