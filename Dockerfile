FROM python:3.12

RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Create and change to the app directory.
WORKDIR /app

# Copy the requirements.txt file to the container.
COPY requirements.txt /app/requirements.txt

# Install dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app to the container.
COPY . .

# Give permission to run the script
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "3", "-b", "0.0.0.0:5000", "core.wsgi:app"]

# Development image used by Docker Compose to run the test suite.
FROM python:3.12 AS test
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt
COPY . .
CMD ["sh", "-c", "ruff check . && python -m pytest"]
