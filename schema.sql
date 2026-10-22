CREATE DATABASE IF NOT EXISTS elearning_analytics;
USE elearning_analytics;

CREATE TABLE IF NOT EXISTS courses (
  course_id INT AUTO_INCREMENT PRIMARY KEY,
  course_name VARCHAR(120) NOT NULL UNIQUE,
  category VARCHAR(80) NOT NULL
);

CREATE TABLE IF NOT EXISTS learners (
  learner_id INT AUTO_INCREMENT PRIMARY KEY,
  learner_name VARCHAR(100) NOT NULL,
  roll_no VARCHAR(30) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS enrollments (
  enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
  learner_id INT NOT NULL,
  course_id INT NOT NULL,
  enrolled_at DATE NOT NULL,
  status ENUM('active','completed','paused') NOT NULL DEFAULT 'active',
  FOREIGN KEY (learner_id) REFERENCES learners(learner_id) ON DELETE CASCADE,
  FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE,
  UNIQUE KEY unique_learner_course (learner_id, course_id)
);

CREATE TABLE IF NOT EXISTS activities (
  activity_id INT AUTO_INCREMENT PRIMARY KEY,
  enrollment_id INT NOT NULL,
  activity_date DATE NOT NULL,
  activity_type ENUM('lesson','quiz','video','assignment','reading') NOT NULL,
  completed TINYINT(1) NOT NULL DEFAULT 0,
  FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS practice_results (
  result_id INT AUTO_INCREMENT PRIMARY KEY,
  enrollment_id INT NOT NULL,
  practice_date DATE NOT NULL,
  correct_count INT NOT NULL,
  question_count INT NOT NULL,
  CHECK (correct_count >= 0 AND question_count > 0 AND correct_count <= question_count),
  FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id) ON DELETE CASCADE
);
