import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None
    dict_row = None

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
SQLITE_DATABASE = Path(os.getenv("SQLITE_DATABASE", str(BASE_DIR / "students.db")))
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

app = Flask(__name__)
CORS(app)

KNOWN_ACRONYMS = {
    "CSE", "ECE", "EEE", "IT", "AI", "ML", "AIML",
    "BCA", "MCA", "BBA", "MBA", "BSC", "MSC",
    "BTECH", "MTECH", "BE", "ME", "BCOM", "MCOM"
}


def using_postgres():
    return bool(DATABASE_URL)


def get_db():
    if using_postgres():
        if psycopg is None:
            raise RuntimeError("PostgreSQL driver is not installed.")
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

    connection = sqlite3.connect(SQLITE_DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def sql(query):
    return query.replace("?", "%s") if using_postgres() else query


def init_db():
    connection = get_db()
    try:
        student_id_type = "BIGINT" if using_postgres() else "INTEGER"
        connection.execute(sql(f"""
            CREATE TABLE IF NOT EXISTS students (
                student_id {student_id_type} PRIMARY KEY,
                name TEXT NOT NULL,
                course TEXT NOT NULL,
                marks REAL NOT NULL CHECK(marks >= 0 AND marks <= 100)
            )
        """))
        connection.commit()
    finally:
        connection.close()


def valid_student_id(value):
    return value.isdigit() and 1 <= len(value) <= 12


def valid_words(value):
    return bool(value.strip()) and all(
        word.isalpha() for word in value.strip().split()
    )


def format_name(value):
    return " ".join(word.capitalize() for word in value.strip().split())


def format_course(value):
    result = []
    for word in value.strip().split():
        upper = word.upper()
        if upper in KNOWN_ACRONYMS:
            result.append(upper)
        else:
            result.append(word.capitalize())
    return " ".join(result)


def student_from_row(row):
    return {
        "id": str(row["student_id"]),
        "name": row["name"],
        "course": row["course"],
        "marks": row["marks"]
    }


def error_response(message, status=400):
    return jsonify({"message": message}), status


def database_error_message():
    if using_postgres():
        return "Database connection failed. Check DATABASE_URL in Vercel environment variables."
    if os.getenv("VERCEL"):
        return "Persistent database is not configured. Add DATABASE_URL in Vercel environment variables."
    return "Database error. Please try again."


@app.route("/", methods=["GET"])
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/style.css", methods=["GET"])
def style_css():
    return send_from_directory(FRONTEND_DIR, "style.css")


@app.route("/script.js", methods=["GET"])
def script_js():
    return send_from_directory(FRONTEND_DIR, "script.js")


@app.route("/health", methods=["GET"])
def health():
    database = "postgresql" if using_postgres() else "sqlite"
    try:
        connection = get_db()
        connection.execute("SELECT 1")
        connection.close()
        return jsonify({
            "status": "ok",
            "message": "Backend and database are running.",
            "database": database
        }), 200
    except Exception:
        return jsonify({
            "status": "error",
            "message": database_error_message(),
            "database": database
        }), 503


@app.route("/students", methods=["POST"])
def add_student():
    data = request.get_json(silent=True) or {}
    student_id = str(data.get("id", "")).strip()
    raw_name = str(data.get("name", "")).strip()
    raw_course = str(data.get("course", "")).strip()
    marks = data.get("marks")

    if not valid_student_id(student_id):
        return error_response("Student ID must contain 1–12 digits only.")
    if not valid_words(raw_name):
        return error_response("Student name must contain alphabets and spaces only.")
    if not valid_words(raw_course):
        return error_response("Course must contain alphabets and spaces only.")

    try:
        marks = float(marks)
    except (ValueError, TypeError):
        return error_response("Marks must be a number.")

    if not 0 <= marks <= 100:
        return error_response("Marks must be between 0 and 100.")

    name = format_name(raw_name)
    course = format_course(raw_course)

    try:
        connection = get_db()
        connection.execute(
            sql("INSERT INTO students (student_id, name, course, marks) VALUES (?, ?, ?, ?)"),
            (int(student_id), name, course, marks)
        )
        connection.commit()
    except (sqlite3.IntegrityError, Exception) as exc:
        # Keep duplicate IDs user-friendly while still returning a safe DB error.
        if isinstance(exc, sqlite3.IntegrityError) or "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            return error_response("Student ID already exists.", 409)
        return error_response(database_error_message(), 500)
    finally:
        if "connection" in locals():
            connection.close()

    return jsonify({
        "message": "Student added successfully.",
        "student": {"id": student_id, "name": name, "course": course, "marks": marks}
    }), 201


@app.route("/students", methods=["GET"])
def get_students():
    query = request.args.get("search", "").strip().lower()
    try:
        connection = get_db()
        if query:
            rows = connection.execute(sql("""
                SELECT student_id, name, course, marks
                FROM students
                WHERE CAST(student_id AS TEXT) LIKE ?
                   OR LOWER(name) LIKE ?
                   OR LOWER(course) LIKE ?
                ORDER BY student_id
            """), (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
        else:
            rows = connection.execute(sql("""
                SELECT student_id, name, course, marks
                FROM students ORDER BY student_id
            """)).fetchall()
        return jsonify([student_from_row(row) for row in rows]), 200
    except Exception:
        return error_response(database_error_message(), 500)
    finally:
        if "connection" in locals():
            connection.close()


@app.route("/students/stats", methods=["GET"])
def student_stats():
    try:
        connection = get_db()
        row = connection.execute(sql("""
            SELECT COUNT(*) AS total_students,
                   COALESCE(AVG(marks), 0) AS average_marks,
                   COALESCE(MAX(marks), 0) AS top_score
            FROM students
        """)).fetchone()
        return jsonify({
            "total_students": row["total_students"],
            "average_marks": round(float(row["average_marks"]), 2),
            "top_score": float(row["top_score"])
        }), 200
    except Exception:
        return error_response(database_error_message(), 500)
    finally:
        if "connection" in locals():
            connection.close()


@app.route("/students/<student_id>", methods=["GET"])
def search_student(student_id):
    if not valid_student_id(student_id):
        return error_response("Student ID must contain 1–12 digits only.")
    try:
        connection = get_db()
        row = connection.execute(sql("""
            SELECT student_id, name, course, marks
            FROM students WHERE student_id = ?
        """), (int(student_id),)).fetchone()
        if row is None:
            return error_response("Student not found.", 404)
        return jsonify(student_from_row(row)), 200
    except Exception:
        return error_response(database_error_message(), 500)
    finally:
        if "connection" in locals():
            connection.close()


@app.route("/students/<student_id>", methods=["PUT"])
def update_student(student_id):
    if not valid_student_id(student_id):
        return error_response("Student ID must contain 1–12 digits only.")

    data = request.get_json(silent=True) or {}
    raw_name = str(data.get("name", "")).strip()
    raw_course = str(data.get("course", "")).strip()
    marks = data.get("marks")

    if not valid_words(raw_name):
        return error_response("Student name must contain alphabets and spaces only.")
    if not valid_words(raw_course):
        return error_response("Course must contain alphabets and spaces only.")
    try:
        marks = float(marks)
    except (ValueError, TypeError):
        return error_response("Marks must be a number.")
    if not 0 <= marks <= 100:
        return error_response("Marks must be between 0 and 100.")

    name = format_name(raw_name)
    course = format_course(raw_course)

    try:
        connection = get_db()
        cursor = connection.execute(sql("""
            UPDATE students SET name = ?, course = ?, marks = ?
            WHERE student_id = ?
        """), (name, course, marks, int(student_id)))
        connection.commit()
        if cursor.rowcount == 0:
            return error_response("Student not found.", 404)
    except Exception:
        return error_response(database_error_message(), 500)
    finally:
        if "connection" in locals():
            connection.close()

    return jsonify({
        "message": "Student updated successfully.",
        "student": {"id": student_id, "name": name, "course": course, "marks": marks}
    }), 200


@app.route("/students/<student_id>", methods=["DELETE"])
def delete_student(student_id):
    if not valid_student_id(student_id):
        return error_response("Student ID must contain 1–12 digits only.")
    try:
        connection = get_db()
        cursor = connection.execute(sql("DELETE FROM students WHERE student_id = ?"), (int(student_id),))
        connection.commit()
        if cursor.rowcount == 0:
            return error_response("Student not found.", 404)
        return jsonify({"message": "Student deleted successfully."}), 200
    except Exception:
        return error_response(database_error_message(), 500)
    finally:
        if "connection" in locals():
            connection.close()


# Initialize local SQLite automatically. On Vercel, a DATABASE_URL is recommended
# for persistent production data; otherwise Vercel's ephemeral filesystem is used.
try:
    init_db()
except Exception:
    # Let the health/API endpoints return a useful configuration error rather than
    # making the deployment fail during import.
    pass


if __name__ == "__main__":
    app.run(debug=True, port=5000)
