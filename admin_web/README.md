# SmartStudy Admin Web Panel

This is the Admin Web Panel for the SmartStudy system. It allows university administrators to manage departments, teachers, students, courses, sections, and semesters.

## Directory Structure

- `backend/`: FastAPI Python application (port `8001`).
- `frontend/`: React + Vite client (port `5173`).
- `docker-compose.yml`: Spins up PostgreSQL database.

## Getting Started

### 1. Database Setup

Spin up the PostgreSQL database container:
```bash
docker-compose up -d
```

### 2. Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Seed the admin user and create database tables:
   ```bash
   python init_db.py
   ```
4. Start the FastAPI development server:
   ```bash
   uvicorn main:app --reload --port 8001
   ```

### 3. Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:5173` in your browser.
