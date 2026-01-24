# Run the project using Docker in the following steps

# Development
- docker-compose --env-file .env.dev -f docker-compose-dev.yml build
- docker-compose --env-file .env.dev -f docker-compose-dev.yml up -d

# Initial steps to set up DB
- docker exec -it main-app sh
- python manage.py create_db
- flask db stamp head 
- flask db upgrade 
