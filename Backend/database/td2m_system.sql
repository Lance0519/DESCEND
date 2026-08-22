CREATE DATABASE IF NOT EXISTS t2dm_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 't2dm_app'@'localhost' IDENTIFIED BY 'StrongPass123!';
CREATE USER IF NOT EXISTS 't2dm_app'@'127.0.0.1' IDENTIFIED BY 'StrongPass123!';

GRANT ALL PRIVILEGES ON t2dm_system.* TO 't2dm_app'@'localhost';
GRANT ALL PRIVILEGES ON t2dm_system.* TO 't2dm_app'@'127.0.0.1';
FLUSH PRIVILEGES;


"eto hiwalay to"

CREATE TABLE IF NOT EXISTS users (
id INT AUTO_INCREMENT PRIMARY KEY,
name VARCHAR(120) NOT NULL,
email VARCHAR(255) NOT NULL,
password_hash VARCHAR(255) NOT NULL,
role VARCHAR(20) NOT NULL DEFAULT 'user',
is_active BOOLEAN NOT NULL DEFAULT TRUE,
failed_login_attempts INT NOT NULL DEFAULT 0,
locked_until DATETIME NULL,
reset_token_hash VARCHAR(255) NULL,
reset_token_expires_at DATETIME NULL,
last_login_at DATETIME NULL,
created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
UNIQUE KEY uq_users_email (email),
KEY ix_users_email (email)
);

CREATE TABLE IF NOT EXISTS assessments (
id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT NULL,
title VARCHAR(160) NOT NULL DEFAULT 'Assessment Record',
created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
bmi FLOAT NOT NULL,
weighted_family_score FLOAT NOT NULL,
payload_json TEXT NOT NULL,
CONSTRAINT fk_assessments_user
FOREIGN KEY (user_id) REFERENCES users(id)
ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS prediction_results (
id INT AUTO_INCREMENT PRIMARY KEY,
assessment_id INT NOT NULL,
target_key VARCHAR(50) NOT NULL,
target_label VARCHAR(120) NOT NULL,
probability FLOAT NOT NULL,
risk_band VARCHAR(20) NOT NULL,
CONSTRAINT fk_prediction_results_assessment
FOREIGN KEY (assessment_id) REFERENCES assessments(id)
ON DELETE CASCADE
);
