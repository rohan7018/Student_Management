CREATE TABLE IF NOT EXISTS students (
    student_id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    course TEXT NOT NULL,
    marks REAL NOT NULL CHECK (marks >= 0 AND marks <= 100)
);
