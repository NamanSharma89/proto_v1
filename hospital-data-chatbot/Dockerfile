FROM python:3.9-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Use uv to install dependencies
RUN uv pip install -e .

# Set up for gunicorn
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT