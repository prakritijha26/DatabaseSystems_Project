
-- Sample data for What-If Database
-- Run only in whatif_practice.

INSERT INTO students
    (student_id, student_name, department, year_of_study)
SELECT
    n,
    'Student ' || n,
    CASE WHEN n % 2 = 0 THEN 'CSE-DS' ELSE 'CSE' END,
    2
FROM generate_series(1001, 1030) AS n;

INSERT INTO courses (course_code, course_name, credits) VALUES
('DS201', 'Probability and Statistics', 4),
('CS202', 'Database Systems', 4),
('CS203', 'Computer Networks', 4),
('DS204', 'Exploratory Data Analysis', 4),
('CS205', 'Java Programming', 2);

INSERT INTO enrollments (student_id, course_id, semester)
SELECT s.student_id, c.course_id, 3
FROM students s
CROSS JOIN courses c;

INSERT INTO attendance
    (enrollment_id, classes_conducted, classes_attended)
SELECT
    e.enrollment_id,
    40,
    CASE
        WHEN s.student_id % 5 = 0 THEN 25
        WHEN s.student_id % 5 = 1 THEN 30
        ELSE 36
    END
FROM enrollments e
JOIN students s ON s.student_id = e.student_id;

INSERT INTO marks (enrollment_id, score)
SELECT
    e.enrollment_id,
    60 + ((s.student_id + c.course_id * 7) % 36)
FROM enrollments e
JOIN students s ON s.student_id = e.student_id
JOIN courses c ON c.course_id = e.course_id;
