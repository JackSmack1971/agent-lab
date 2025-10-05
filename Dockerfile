# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed (for potential future extensions)
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Copy requirements first for better caching
COPY --chown=app:app requirements.lock .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.lock

# Copy application code
COPY --chown=app:app . .

# Expose the port Gradio uses
EXPOSE 7860

# Set environment variable for host binding
ENV GRADIO_SERVER_HOST=0.0.0.0

# Run the application
CMD ["python", "app.py"]