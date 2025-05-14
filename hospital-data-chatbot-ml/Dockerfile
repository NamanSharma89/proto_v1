# Dockerfile.ml-api
FROM python:3.9-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Copy project files
COPY . .

# Use uv to install dependencies
RUN uv pip install -e .

# Make directories
RUN mkdir -p data/models_data/features

# Expose the API port
EXPOSE 8080

# Start the ML API server
CMD ["uvicorn", "app.ml.mcp.api:app", "--host", "0.0.0.0", "--port", "8080"]