-- =========================================================
-- FitTrack AI - Database Schema
-- Run this file in MySQL to create the database and tables.
--   mysql -u root -p < fittrack_db.sql
-- =========================================================

CREATE DATABASE IF NOT EXISTS fittrack_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE fittrack_db;

-- =========================================================
-- Table: users
-- =========================================================
CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    full_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(150) NOT NULL UNIQUE,
    phone           VARCHAR(20),
    age             INT,
    gender          VARCHAR(20),
    height          DECIMAL(5,2)   NOT NULL,   -- in cm
    initial_weight  DECIMAL(5,2)   NOT NULL,   -- in kg
    password        VARCHAR(255)   NOT NULL,   -- hashed password
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =========================================================
-- Table: weight_history
-- =========================================================
CREATE TABLE IF NOT EXISTS weight_history (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    weight       DECIMAL(5,2) NOT NULL,
    record_date  DATE NOT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_weight_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_weight_user_date (user_id, record_date)
) ENGINE=InnoDB;

-- =========================================================
-- Table: workouts
-- =========================================================
CREATE TABLE IF NOT EXISTS workouts (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    user_id          INT NOT NULL,
    workout_type     VARCHAR(50) NOT NULL,
    duration         INT NOT NULL,          -- minutes
    calories_burned  INT NOT NULL,
    workout_date     DATE NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_workout_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_workout_user_date (user_id, workout_date)
) ENGINE=InnoDB;

-- =========================================================
-- Table: meals
-- =========================================================
CREATE TABLE IF NOT EXISTS meals (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    food_name   VARCHAR(100) NOT NULL,
    calories    INT NOT NULL,
    meal_type   VARCHAR(30) NOT NULL,
    meal_date   DATE NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_meal_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_meal_user_date (user_id, meal_date)
) ENGINE=InnoDB;

-- =========================================================
-- Table: steps
-- =========================================================
CREATE TABLE IF NOT EXISTS steps (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    user_id          INT NOT NULL,
    steps            INT NOT NULL,
    distance         DECIMAL(6,2) NOT NULL,   -- km
    calories_burned  INT NOT NULL,
    record_date      DATE NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_steps_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_steps_user_date (user_id, record_date)
) ENGINE=InnoDB;

-- =========================================================
-- Table: fitness_goals
-- =========================================================
CREATE TABLE IF NOT EXISTS fitness_goals (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT NOT NULL,
    goal_type      VARCHAR(50) NOT NULL,
    target_value   DECIMAL(10,2) NOT NULL,
    current_value  DECIMAL(10,2) NOT NULL DEFAULT 0,
    target_date    DATE,
    status         VARCHAR(20) NOT NULL DEFAULT 'Active',
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_goal_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_goal_user (user_id)
) ENGINE=InnoDB;
