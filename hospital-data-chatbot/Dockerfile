# Dockerfile - Update with entrypoint script
FROM python:3.9-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Set default environment (will be overridden at runtime)
ENV APP_ENV=dev-cloud
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV DATA_DIR=data
ENV WAIT_FOR_DB=true

# Copy project files
COPY . .

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

# Use uv to install dependencies
RUN uv pip install -e .

# Expose the application port
EXPOSE 8080

# Use the entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Start the application with environment-aware settings
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]