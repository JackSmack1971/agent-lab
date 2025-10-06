# docs/developer/AGENTS.md

## Project Overview

Agent Lab is a Gradio-based platform for testing AI agents across multiple models

**Tech Stack**: Python 3.11+, Gradio v5, pydantic-ai, OpenRouter API, pytest

**Architecture**: 3-layer (UI → Runtime → API)

## Code Standards

- Use type hints for all functions and classes
- Write docstrings in Google style format
- Follow PEP 8 with black formatting
- Minimum test coverage: 90%
- Use pydantic models for all data validation

## Testing Requirements

- Location: tests/ directory mirrors src/ structure
- Run tests: `pytest tests/ -v --cov=src --cov-report=term-missing`
- Each feature must include:
  - Unit tests for all functions
  - Integration tests for component interactions
  - Example usage in tests/examples/
- All tests must pass before committing

## Git Workflow

- No new branches (work on current branch)
- Atomic commits (one logical change per commit)
- Commit message format: "type(scope): description"
  - Types: feat, fix, docs, test, refactor, perf, chore
- Never amend existing commits
- Always ensure clean worktree: `git status` should show "working tree clean"

## File Organization

- Components: src/components/ (UI and Gradio interfaces)
- Services: src/services/ (business logic, API integrations)
- Models: src/models/ (pydantic data models)
- Utils: src/utils/ (helper functions)
- Tests: tests/ (mirrors src/ structure)

## Dependencies Management

- Use requirements.txt for Python dependencies
- Pin major versions, allow minor updates
- Document any new dependencies in comments

## PR and Review Standards

- All changes require review before merging
- PR description must include:
  - What changed and why
  - How to test the changes
  - Any breaking changes or migrations
- Link to relevant issue or feature request