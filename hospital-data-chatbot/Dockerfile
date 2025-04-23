# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Set default environment (will be overridden at runtime)
ENV APP_ENV=dev_cloud
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Copy project files
COPY . .

# Use uv to install dependencies
RUN uv pip install -e .

# Expose the application port
EXPOSE 8080

# Start the application with environment-aware settings
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT