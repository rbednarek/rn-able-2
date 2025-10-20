## RN-able 2

# Django project supporting informatics analyses


Libraries to manage with poetry:
- python-decouple
- psycopg2-binary
- postgres

# RN-able 2 Setup Instructions

## Prerequisites

- Python 3.8+
- PostgreSQL 12+

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/rnable.git
cd rnable
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup PostgreSQL

Install PostgreSQL:
- Ubuntu/Debian: `sudo apt-get install postgresql`
- Mac: `brew install postgresql`
- Windows: Download from postgresql.org

Create database and user:
```bash
sudo -u postgres psql
```

In PostgreSQL shell:
```sql
CREATE DATABASE rnable_db;
CREATE USER rnable_user WITH PASSWORD 'choose_a_password';
GRANT ALL PRIVILEGES ON DATABASE rnable_db TO rnable_user;
\c rnable_db
ALTER SCHEMA public OWNER TO rnable_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO rnable_user;
\q
```

### 4. Configure Environment

Copy example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your database password:
```bash
DB_PASSWORD=the_password_you_chose
```

### 5. Run Migrations
```bash
python manage.py migrate
```

### 6. Run Server
```bash
python manage.py runserver
```

Visit: http://127.0.0.1:8000/
