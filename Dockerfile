# Panoptes Telegram Bot - Dockerfile
# Production-ready Docker image for the Plume Cloud Monitoring Bot

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Create a non-root user for security
RUN groupadd --gid 1000 botuser && \
    useradd --uid 1000 --gid 1000 --no-create-home --shell /bin/bash botuser

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./

# Change ownership to non-root user
RUN chown -R botuser:botuser /app

# Switch to non-root user
USER botuser

# Run the bot
CMD ["python", "panoptes_bot.py"]
