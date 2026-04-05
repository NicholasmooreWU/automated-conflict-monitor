# Contributing to OSINT Conflict Monitor

First off, thank you for considering contributing to OSINT Conflict Monitor! It's people like you that make this tool better for everyone.

##  Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)

##  Code of Conduct

This project and everyone participating in it is governed by a commitment to creating a welcoming and inclusive environment. By participating, you are expected to uphold this standard.

### Our Standards

- **Be respectful**: Treat everyone with respect and kindness
- **Be collaborative**: Work together towards common goals
- **Be patient**: Remember that everyone has different experience levels
- **Be constructive**: Provide helpful feedback and suggestions

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples** to demonstrate the steps
- **Describe the behavior you observed** and what you expected
- **Include screenshots** if relevant
- **Note your environment** (OS, Python version, etc.)

**Bug Report Template:**
```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
 - OS: [e.g., Windows 11, Ubuntu 22.04]
 - Python Version: [e.g., 3.10.5]
 - Browser: [e.g., Chrome 120]
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Use a clear and descriptive title**
- **Provide a detailed description** of the suggested enhancement
- **Explain why this enhancement would be useful**
- **List any alternative solutions** you've considered

### Pull Requests

Good pull requests (patches, improvements, new features) are fantastic help. They should remain focused in scope and avoid containing unrelated commits.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- Virtual environment tool (venv, conda, etc.)

### Setup Steps

1. **Fork the repository**
   ```bash
   # Click the "Fork" button on GitHub
   ```

2. **Clone your fork**
   ```bash
   git clone https://github.com/your-username/osint-conflict-monitor.git
   cd osint-conflict-monitor
   ```

3. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

5. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

6. **Set up environment variables**
   ```bash
   echo "API_KEY=your_test_api_key" > .env
   ```

## Pull Request Process

1. **Update documentation** for any changed functionality
2. **Add tests** for new features or bug fixes
3. **Ensure all tests pass**: `pytest`
4. **Follow coding standards** (see below)
5. **Update the README.md** if needed
6. **Create a clear PR description** explaining your changes

### PR Description Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## How Has This Been Tested?
Describe the tests you ran to verify your changes.

## Checklist
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
```

##  Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 100 characters maximum
- **Docstrings**: Google style docstrings
- **Type hints**: Use type hints for function parameters and return values
- **Formatting**: Use `black` for automatic formatting

```bash
# Format your code
black .

# Check for style issues
flake8 .
```

### Code Organization

```python
# Good: Clear, descriptive names
def analyze_sentiment(text: str) -> float:
    """
    Analyze the sentiment of a given text.
    
    Args:
        text: The input text to analyze
        
    Returns:
        float: Sentiment score between -1.0 and 1.0
    """
    # Implementation
    pass

# Bad: Unclear, abbreviated names
def an_sent(t):
    # Implementation
    pass
```

### Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests after the first line

```
Good examples:
- Add sentiment filtering to dashboard
- Fix path traversal vulnerability in collector
- Update README with Docker instructions

Bad examples:
- Fixed stuff
- Changes
- asdfasdf
```

##  Testing Guidelines

### Writing Tests

- Write tests for all new features and bug fixes
- Aim for >80% code coverage
- Use descriptive test names that explain what they test
- Follow the AAA pattern: Arrange, Act, Assert

```python
def test_sanitize_filename_removes_dangerous_chars():
    """Test that dangerous characters are removed from filenames"""
    # Arrange
    collector = IntelCollector("test_key")
    dangerous = "../../../etc/passwd"
    
    # Act
    result = collector._sanitize_filename(dangerous)
    
    # Assert
    assert ".." not in result
    assert "/" not in result
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_collector.py

# Run specific test
pytest tests/test_collector.py::TestIntelCollector::test_sanitize_filename
```

##  Issue and PR Labels

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements or additions to documentation
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed
- `security`: Security-related issues

##  Questions?

- Open an issue with the `question` label
- Reach out to the maintainers

##  Recognition

Contributors will be recognized in:
- The repository's README
- Release notes for their contributions
- A CONTRIBUTORS.md file (coming soon)

Thank you for contributing to OSINT Conflict Monitor! 
