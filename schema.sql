
-- What-If Database: schema
-- Target database: whatif_practice
-- This script creates objects; it does not drop existing objects.

CREATE TABLE students (
    student_id INTEGER PRIMARY KEY,
    student_name VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL,
    year_of_study INTEGER NOT NULL
        CHECK (year_of_study BETWEEN 1 AND 4)
);

CREATE TABLE courses (
    course_id INTEGER PRIMARY KEY,
    course_code VARCHAR(10) UNIQUE NOT NULL,
    course_name VARCHAR(100) NOT NULL,
    credits INTEGER NOT NULL CHECK (credits BETWEEN 1 AND 6)
);

CREATE TABLE enrollments (
    enrollment_id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL
        REFERENCES students(student_id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL
        REFERENCES courses(course_id) ON DELETE CASCADE,
    semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
    UNIQUE (student_id, course_id, semester)
);

CREATE TABLE attendance (
    attendance_id INTEGER PRIMARY KEY,
    enrollment_id INTEGER NOT NULL UNIQUE
        REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
    classes_conducted INTEGER NOT NULL CHECK (classes_conducted >= 0),
    classes_attended INTEGER NOT NULL CHECK (
        classes_attended >= 0
        AND classes_attended <= classes_conducted
    )
);

CREATE TABLE marks (
    mark_id INTEGER PRIMARY KEY,
    enrollment_id INTEGER NOT NULL UNIQUE
        REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
    score NUMERIC(5,2) NOT NULL CHECK (score BETWEEN 0 AND 100)
);

-- Attendance eligibility: 75% or above is eligible.
CREATE VIEW attendance_eligibility AS
SELECT
    s.student_id,
    s.student_name,
    c.course_code,
    COALESCE(a.classes_attended, 0) AS classes_attended,
    COALESCE(a.classes_conducted, 0) AS classes_conducted,
    CASE
        WHEN a.enrollment_id IS NULL THEN 0
        WHEN a.classes_conducted = 0 THEN NULL
        ELSE ROUND(
            100.0 * a.classes_attended / a.classes_conducted, 2
        )
    END AS attendance_percentage,
    CASE
        WHEN a.enrollment_id IS NULL THEN 'NO'
        WHEN a.classes_conducted = 0 THEN 'UNKNOWN'
        WHEN 100.0 * a.classes_attended / a.classes_conducted >= 75
            THEN 'YES'
        ELSE 'NO'
    END AS exam_eligible
FROM students s
JOIN enrollments e ON e.student_id = s.student_id
JOIN courses c ON c.course_id = e.course_id
LEFT JOIN attendance a ON a.enrollment_id = e.enrollment_id;

-- Weighted average score, not an official institutional CGPA.
CREATE VIEW student_performance AS
SELECT
    s.student_id,
    s.student_name,
    ROUND(
        SUM(m.score * c.credits) / NULLIF(SUM(c.credits), 0), 2
    ) AS weighted_average_score,
    -- Demonstration grade bands, not an official institutional grading policy.
    ROUND(SUM((CASE WHEN m.score >= 90 THEN 10 WHEN m.score >= 80 THEN 9
                    WHEN m.score >= 70 THEN 8 WHEN m.score >= 60 THEN 7
                    WHEN m.score >= 50 THEN 6 WHEN m.score >= 40 THEN 5
                    ELSE 0 END) * c.credits)::NUMERIC
          / NULLIF(SUM(c.credits), 0), 2) AS weighted_gpa
FROM students s
JOIN enrollments e ON e.student_id = s.student_id
JOIN courses c ON c.course_id = e.course_id
JOIN marks m ON m.enrollment_id = e.enrollment_id
GROUP BY s.student_id, s.student_name;

-- Audit log for actual mark updates.
CREATE TABLE mark_change_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mark_id INTEGER NOT NULL,
    old_score NUMERIC(5,2),
    new_score NUMERIC(5,2),
    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE FUNCTION log_mark_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO mark_change_log (mark_id, old_score, new_score)
    VALUES (OLD.mark_id, OLD.score, NEW.score);
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_log_mark_change
AFTER UPDATE OF score ON marks
FOR EACH ROW
WHEN (OLD.score IS DISTINCT FROM NEW.score)
EXECUTE FUNCTION log_mark_change();

-- Foreign-key lookup paths for cascades and metric joins.
CREATE INDEX enrollments_course_idx ON enrollments(course_id);
