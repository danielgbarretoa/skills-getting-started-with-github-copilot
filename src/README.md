# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities

## Requirements

- Python 3.10+
- Docker (optional, for running PostgreSQL locally)

## Getting Started

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Start PostgreSQL with Docker Compose (from repository root):

   ```
   docker compose up -d postgres
   ```

3. Set the database connection URL:

   ```
   export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/mergington"
   ```

4. Run the application:

   ```
   uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |
| DELETE | `/activities/{activity_name}/signup?email=student@mergington.edu` | Unregister from an activity                                         |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in PostgreSQL.
