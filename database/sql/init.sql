-- StudyMate 数据库初始化脚本
-- MySQL 8.0

CREATE DATABASE IF NOT EXISTS studymate
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE studymate;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    openid VARCHAR(64) NOT NULL UNIQUE,
    nickname VARCHAR(64) DEFAULT '' NOT NULL,
    avatar VARCHAR(256) DEFAULT '' NOT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_openid (openid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 学习任务表
CREATE TABLE IF NOT EXISTS study_tasks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    date DATE NOT NULL,
    subject VARCHAR(32) NOT NULL COMMENT '科目：数学/英语/政治/408',
    content VARCHAR(512) NOT NULL COMMENT '任务内容',
    start_time TIME DEFAULT NULL COMMENT '开始时间',
    end_time TIME DEFAULT NULL COMMENT '结束时间',
    status VARCHAR(16) DEFAULT 'pending' COMMENT 'pending/done/cancelled',
    plan_source VARCHAR(16) DEFAULT 'manual' COMMENT 'manual/excel/json/pdf',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_date (user_id, date),
    INDEX idx_user_status (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 学习记录表
CREATE TABLE IF NOT EXISTS study_records (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    task_id INT DEFAULT NULL,
    start_time DATETIME NOT NULL COMMENT '开始时间',
    end_time DATETIME DEFAULT NULL COMMENT '结束时间',
    duration INT DEFAULT 0 COMMENT '学习时长（秒）',
    record_type VARCHAR(16) DEFAULT 'focus' COMMENT 'pomodoro/countdown/focus',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES study_tasks(id) ON DELETE SET NULL,
    INDEX idx_user_start (user_id, start_time),
    INDEX idx_user_type (user_id, record_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- AI 分析记录表
CREATE TABLE IF NOT EXISTS ai_analysis (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    analysis_type VARCHAR(32) NOT NULL COMMENT 'daily_summary/plan_optimization/qa',
    input_data TEXT COMMENT '分析输入',
    output_data TEXT COMMENT '分析结果',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_type (user_id, analysis_type),
    INDEX idx_user_time (user_id, create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;