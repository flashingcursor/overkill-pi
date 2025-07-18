# Contributing to OVERKILL-PI

Thank you for your interest in contributing to OVERKILL-PI! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect differing viewpoints and experiences

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/overkill-pi.git
   cd overkill-pi
   ```
3. Add upstream remote:
   ```bash
   git remote add upstream https://github.com/flashingcursor/overkill-pi.git
   ```

## Development Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Making Changes

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Write Code

- Follow the existing code style
- Add docstrings to all functions and classes
- Use type hints where appropriate
- Keep functions focused and single-purpose

### 3. Code Style

We use Black for code formatting and flake8 for linting:

```bash
# Format code
black overkill/

# Check linting
flake8 overkill/

# Type checking
mypy overkill/
```

### 4. Write Tests

- Add tests for new functionality
- Ensure existing tests pass
- Aim for >80% code coverage

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=overkill --cov-report=html
```

### 5. Update Documentation

- Update README.md if adding features
- Update INSTALL.md for installation changes
- Add/update docstrings
- Update TESTING.md if adding test cases

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Test additions or changes
- **chore**: Build process or auxiliary tool changes

### Examples

```
feat(overclock): add silicon quality testing

Implement comprehensive stress testing to grade silicon quality.
Tests run progressively from stock to extreme profiles.

Closes #123
```

```
fix(thermal): correct PWM frequency calculation

PWM frequency was calculated in Hz instead of kHz,
causing incorrect fan speeds on some systems.
```

## Pull Request Process

1. **Update your fork**:
   ```bash
   git fetch upstream
   git checkout master
   git merge upstream/master
   ```

2. **Rebase your feature branch**:
   ```bash
   git checkout feature/your-feature
   git rebase master
   ```

3. **Push to your fork**:
   ```bash
   git push origin feature/your-feature
   ```

4. **Create Pull Request**:
   - Go to GitHub and create a PR from your fork
   - Fill in the PR template
   - Link any related issues

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] Commit messages follow guidelines
- [ ] PR description explains changes clearly

## Testing on Raspberry Pi

If you're developing features that require Pi hardware:

1. Test on actual Raspberry Pi 5
2. Test with both Armbian and Raspberry Pi OS
3. Test with different cooling solutions
4. Verify no regressions in core functionality

## Areas for Contribution

### High Priority

- Additional overclock profiles for specific use cases
- Improved fan curve algorithms
- Better error handling and recovery
- Additional Kodi addon repositories
- Performance optimizations

### Feature Ideas

- Web-based monitoring interface
- Mobile app for remote control
- Integration with Home Assistant
- Custom themes for the TUI
- Benchmark suite integration

### Documentation

- Tutorials for specific use cases
- Video guides
- Translations
- Troubleshooting guides

## Getting Help

- Check existing issues and discussions
- Join our Discord server (if available)
- Ask questions in GitHub Discussions
- Tag @flashingcursor for code reviews

## Release Process

Maintainers will:

1. Update version numbers
2. Update CHANGELOG.md
3. Create release tags
4. Build and test on multiple platforms
5. Publish release notes

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in:
- README.md acknowledgments
- Release notes
- Contributors page on GitHub

Thank you for helping make OVERKILL-PI better! 🚀