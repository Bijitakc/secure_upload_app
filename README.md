# Secure Upload App

A secure file upload service built with Flask and AWS S3. Files **never touch the backend**, and access is controlled using **pre-signed URLs** with automatic expiration. Ideal for handling sensitive data in regulated industries (healthcare, fintech, legal, HR).

## Getting Started

### Copy the env variables from .env.sample to .env.sample and add the required variables.

### Run the project using Docker by following the following steps
- docker-compose --env-file .env.dev -f docker-compose-dev.yml build
- docker-compose --env-file .env.dev -f docker-compose-dev.yml up -d

### Initial steps to set up DB
- docker exec -it main-app sh
- python manage.py create_db
- flask db stamp head 
- flask db upgrade 
