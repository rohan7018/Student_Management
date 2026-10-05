# Student Performance Management System

A full-stack student management dashboard built with HTML, CSS, JavaScript, Python Flask and SQL.

## Features

- Add, search, update and delete students
- Search through the SQL database by ID, name or course
- Sort by name, marks or student ID
- Performance statistics: total students, average marks and top score
- Student ID validation: **1–12 digits only**
- Student ID supports 12-digit values in PostgreSQL using `BIGINT`
- Name/course validation and automatic formatting (`cse` → `CSE`, `rahul sharma` → `Rahul Sharma`)
- Student ID is locked during editing because it is the primary key
- Inline validation, loading states and friendly error messages
- Same-origin frontend/backend when deployed to Vercel
- PostgreSQL support through `DATABASE_URL`
- SQLite fallback for local development

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Open `http://127.0.0.1:5000`.

## Vercel deployment

Vercel supports Flask applications directly with zero-configuration Python deployment. This project keeps `app.py` and `requirements.txt` at the project root and serves the frontend from Flask.

1. Push this folder to GitHub.
2. Import the repository into Vercel.
3. Keep the Vercel **Root Directory** at the repository root.
4. Deploy.
5. For persistent production data, add a managed PostgreSQL database and set the Vercel environment variable:

```text
DATABASE_URL=your-postgresql-connection-string
```

### Database note

SQLite is suitable for local development. Vercel deployments should not use a local SQLite file as the persistent production database. Use PostgreSQL by setting `DATABASE_URL` for production data.

The PostgreSQL schema uses `BIGINT` for `student_id`, so the requested maximum of 12 digits is supported.

## API

- `GET /health`
- `GET /students?search=...`
- `POST /students`
- `GET /students/<student_id>`
- `PUT /students/<student_id>`
- `DELETE /students/<student_id>`
- `GET /students/stats`

## Test report

See `TEST_REPORT.txt` for the verification results.
