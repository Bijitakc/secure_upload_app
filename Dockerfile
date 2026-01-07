FROM python:3.12

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