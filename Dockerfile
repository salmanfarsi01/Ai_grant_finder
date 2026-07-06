# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for extremely fast python package installations
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install python dependencies using uv
COPY requirements.txt /app/
RUN uv pip install --system --no-cache -r requirements.txt

# Copy project
COPY . /app/

# Expose port
EXPOSE 2323

# Run the application (this can be overridden in docker-compose.yml)
CMD ["python", "manage.py", "runserver", "0.0.0.0:2323"]
