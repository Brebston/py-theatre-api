# Theatre API

This is a simple REST API for theatre management built with **Django Rest Framework**.
The project allows managing plays, actors, genres, theatre halls, performances, tickets and users.

Authentication is implemented using **JWT (SimpleJWT)**.

---

## Installing using GitHub

### 1. Clone the repository

```bash
git clone https://github.com/your-username/theatre-api.git
cd theatre-api
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate   # for Linux / Mac
venv\Scripts\activate      # for Windows
```

### 3. Install requirements

```bash
pip install -r requirements.txt
```

### 4. Set environment variables

Create `.env` file or set variables manually:

```bash
DB_NAME=theatre
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

SECRET_KEY=your-secret-key
DEBUG=True
```

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Load fixtures

```bash
python manage.py loaddata fixtures/users.json
python manage.py loaddata fixtures/theatre.json
```
**Admin login:** \
**email:** admin@admin.com \
**password:** 123

### 7. Create superuser

```bash
python manage.py createsuperuser
```

### 8. Run server

```bash
python manage.py runserver
```

API will be available at:

```
http://127.0.0.1:8000/api/
```

---

## Run with Docker

Docker and docker-compose should be installed.

```bash
docker-compose build
docker-compose up
```

---

## Getting access

### Register user

```http
POST /api/users/register/
```

### Get access token

```http
POST /api/users/token/
```

Use token in header:

```
Authorization: Bearer <access_token>
```

---

## Running tests

```bash
python manage.py test
```

---
