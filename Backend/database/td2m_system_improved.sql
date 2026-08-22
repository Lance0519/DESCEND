-- Improved schema for t2dm_system
-- Version: 2026-05-20
-- Purpose: clearer constraints, indexes, JSON columns, migration tracking, and basic audit/log tables.

CREATE DATABASE IF NOT EXISTS t2dm_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE t2dm_system;

-- Migration/versioning table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(100) NOT NULL PRIMARY KEY,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Users table (aligned with app.models.User)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    failed_login_attempts INT NOT NULL DEFAULT 0,
    locked_until DATETIME NULL,
    reset_token_hash VARCHAR(255) NULL,
    reset_token_expires_at DATETIME NULL,
    last_login_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_users_email (email),
    KEY ix_users_role (role),
    KEY ix_users_last_login (last_login_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Assessments table (aligned with app.models.Assessment)
CREATE TABLE IF NOT EXISTS assessments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    title VARCHAR(160) NOT NULL DEFAULT 'Assessment Record',
    source VARCHAR(50) NULL,
    source_assessment_id VARCHAR(100) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    bmi DOUBLE NOT NULL,
    weighted_family_score DOUBLE NOT NULL,
    payload_json JSON NOT NULL,
    CONSTRAINT fk_assessments_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    KEY ix_assessments_user (user_id),
    KEY ix_assessments_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Prediction results (aligned with app.models.PredictionResult)
CREATE TABLE IF NOT EXISTS prediction_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assessment_id INT NOT NULL,
    model_version VARCHAR(64) NULL,
    target_key VARCHAR(50) NOT NULL,
    target_label VARCHAR(120) NOT NULL,
    probability DOUBLE NOT NULL,
    raw_output_json JSON NULL,
    risk_band VARCHAR(20) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_prediction_results_assessment FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE,
    KEY ix_prediction_assessment (assessment_id),
    KEY ix_prediction_model (model_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Basic audit/logs for security events and actions
CREATE TABLE IF NOT EXISTS user_activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(100) NOT NULL,
    detail TEXT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(512) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_activity_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    KEY ix_user_activity_user (user_id),
    KEY ix_user_activity_action (action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional: sessions table (simple token tracking)
CREATE TABLE IF NOT EXISTS user_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    expires_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    KEY ix_user_sessions_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Example seed: insert migration version for this improved schema
INSERT IGNORE INTO schema_migrations (version, description) VALUES ('2026-05-20_v1', 'Initial improved schema');

-- Notes:
-- 1) This schema uses JSON columns for payloads and raw model outputs (MySQL 5.7+ / MariaDB equivalents required).
-- 2) If you deploy to environments without native JSON support, change JSON -> TEXT and consider adding CHECK constraints.
-- 3) Adjust model_version, indexes, and additional columns to match evolving application needs.

-- End of improved schema
