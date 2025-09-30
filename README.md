# Agent Lab

Agent Lab is a Gradio-based platform for configuring, testing, and comparing AI agents powered by OpenRouter-hosted language mo
 dels.

## Getting Started

### 1. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
Copy the example file and set your credentials:
```bash
cp .env.example .env
```

Edit `.env` and replace the placeholder with your actual OpenRouter API key.

## Running the Application

Launch the development server with:
```bash
python app.py
```

## Notes
- An active OpenRouter API key is required to interact with hosted models.
- Ensure Python 3.11 or 3.12 is used for the best compatibility.
