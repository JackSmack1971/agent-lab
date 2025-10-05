# Agent Lab

[![Test Coverage](https://img.shields.io/badge/coverage->90%25-brightgreen.svg)](tests/README.md)

Agent Lab is a Gradio-based platform for configuring, testing, and comparing AI agents powered by OpenRouter-hosted language models. Features real-time cost monitoring and optimization suggestions to help manage AI conversation expenses.

## Features

### 🤖 Agent Testing
- Configure and test AI agents with multiple OpenRouter-hosted models
- Real-time streaming responses with cancellation support
- Session persistence and management
- Model catalog with dynamic updates and fallbacks
- Comprehensive keyboard shortcuts for enhanced productivity

### 💰 Cost Optimizer
- Real-time cost tracking during conversations
- Budget management and spending alerts
- Historical cost trends and analytics
- AI-powered optimization suggestions (context reduction, model switching, caching)
- Interactive cost visualization with 7-day trends

## Getting Started

### 1. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

For reproducible builds, install from the lockfile:
```bash
pip install -r requirements.lock
```

For development with flexible version ranges:
```bash
pip install -r requirements.txt
```

**Note:** The `requirements.lock` file contains exact versions for consistent CI builds. Update it by installing dependencies and running `pip freeze > requirements.lock`.

### 3. Configure environment variables
Copy the example file and set your credentials:
```bash
cp .env.example .env
```

Edit `.env` and replace the placeholder with your actual OpenRouter API key.

## Running the Application

### Local Development (Python)
Launch the development server with:
```bash
python app.py
```

### Docker Development
For containerized development with Docker:

1. **Build and run with Docker Compose** (recommended):
   ```bash
   # Set your OpenRouter API key
   export OPENROUTER_API_KEY="your-api-key-here"

   # Build and start the container
   docker-compose up --build
   ```

2. **Or build and run manually**:
   ```bash
   # Build the image
   docker build -t agent-lab .

   # Run the container
   docker run -p 7860:7860 \
     -e OPENROUTER_API_KEY="your-api-key-here" \
     -v $(pwd)/data:/app/data \
     agent-lab
   ```

The application will be available at `http://localhost:7860`.

**Note:** Data persistence is handled through volume mounts to the `./data` directory.

## Keyboard Shortcuts

Agent Lab includes comprehensive keyboard shortcut support for enhanced productivity. Press `Ctrl + /` (or `Cmd + /` on Mac) to view all available shortcuts, or see the [complete keyboard shortcuts documentation](docs/keyboard_shortcuts.md) for detailed reference.

## Testing

### Run Tests
```bash
# Run all tests with coverage
pytest --cov=agents --cov=services tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v
```

### Coverage Requirements
- Maintain >90% test coverage for `agents/` and `services/` directories
- See `tests/README.md` for detailed testing documentation

## Notes
- An active OpenRouter API key is required to interact with hosted models.
- Ensure Python 3.11 or 3.12 is used for the best compatibility.
