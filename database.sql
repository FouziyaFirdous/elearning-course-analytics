CREATE DATABASE IF NOT EXISTS elearning_analytics;
USE elearning_analytics;

CREATE TABLE IF NOT EXISTS courses (
    course_id INT PRIMARY KEY AUTO_INCREMENT,
    course_name VARCHAR(100) NOT NULL,
    category VARCHAR(50)
);
CREATE TABLE IF NOT EXISTS learners (
    learner_id INT PRIMARY KEY AUTO_INCREMENT,
    roll_no VARCHAR(30) UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id INT PRIMARY KEY AUTO_INCREMENT,
    learner_id INT NOT NULL,
    course_id INT NOT NULL,
    enrolled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('active', 'completed', 'withdrawn') DEFAULT 'active',
    FOREIGN KEY (learner_id) REFERENCES learners(learner_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);
CREATE TABLE IF NOT EXISTS activities (
    activity_id INT PRIMARY KEY AUTO_INCREMENT,
    enrollment_id INT NOT NULL,
    activity_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    activity_type VARCHAR(50) NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id)
);

INSERT IGNORE INTO courses (course_id, course_name, category) VALUES
(1,'Python Programming','Programming'),
(2,'Data Science','Analytics'),
(3,'Web Development','Web');

INSERT IGNORE INTO learners (learner_id, roll_no) VALUES
(1,'STU101'),(2,'STU102'),(3,'STU103'),(4,'STU104'),(5,'STU105');

INSERT IGNORE INTO enrollments
(enrollment_id, learner_id, course_id, enrolled_at, status) VALUES
(1,1,1,DATE_SUB(NOW(), INTERVAL 30 DAY),'completed'),
(2,2,1,DATE_SUB(NOW(), INTERVAL 20 DAY),'active'),
(3,3,2,DATE_SUB(NOW(), INTERVAL 25 DAY),'completed'),
(4,4,2,DATE_SUB(NOW(), INTERVAL 18 DAY),'active'),
(5,5,3,DATE_SUB(NOW(), INTERVAL 40 DAY),'active'),
(6,1,2,DATE_SUB(NOW(), INTERVAL 10 DAY),'active');

INSERT INTO activities (enrollment_id, activity_date, activity_type, completed) VALUES
(1,DATE_SUB(NOW(), INTERVAL 20 DAY),'Lesson',TRUE),
(1,DATE_SUB(NOW(), INTERVAL 18 DAY),'Quiz',TRUE),
(1,DATE_SUB(NOW(), INTERVAL 15 DAY),'Assignment',TRUE),
(2,DATE_SUB(NOW(), INTERVAL 2 DAY),'Lesson',TRUE),
(2,DATE_SUB(NOW(), INTERVAL 1 DAY),'Quiz',FALSE),
(3,DATE_SUB(NOW(), INTERVAL 12 DAY),'Lesson',TRUE),
(3,DATE_SUB(NOW(), INTERVAL 8 DAY),'Assignment',TRUE),
(4,DATE_SUB(NOW(), INTERVAL 3 DAY),'Lesson',TRUE),
(6,DATE_SUB(NOW(), INTERVAL 5 DAY),'Lesson',FALSE);
