import os
import time
import mysql.connector
from mysql.connector import Error
from flask import current_app


def get_connection():
    # return mysql.connector.connect(
    #     host=os.getenv("DB_HOST", "db"),
    #     port=int(os.getenv("DB_PORT", "3306")),
    #     database=os.getenv("DB_NAME", "accessibility_experiments"),
    #     user=os.getenv("DB_USER", "access_user"),
    #     password=os.getenv("DB_PASSWORD", "access_pass"),
    # )

    return mysql.connector.connect(
        host=current_app.config["DB_HOST"],
        port=int(current_app.config["DB_PORT"]),
        database=current_app.config["DB_NAME"],
        user=current_app.config["DB_USER"],
        password=current_app.config["DB_PASSWORD"],
    )


def init_db():
    max_attempts = 10

    for attempt in range(max_attempts):
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    urls TEXT NOT NULL,
                    include_semantic BOOLEAN NOT NULL DEFAULT FALSE,
                    status VARCHAR(50) NOT NULL DEFAULT 'registered',
                    created_at DATETIME NOT NULL,
                    completed_at DATETIME NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiment_environment (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    experiment_id INT NOT NULL,
                    docker_web_image VARCHAR(255) NULL,
                    docker_evaluator_image VARCHAR(255) NULL,
                    python_version VARCHAR(100) NULL,
                    node_version VARCHAR(100) NULL,
                    chromium_version VARCHAR(255) NULL,
                    axe_version VARCHAR(100) NULL,
                    lighthouse_version VARCHAR(100) NULL,
                    openai_model VARCHAR(100) NULL,
                    execution_seconds FLOAT NULL,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiment_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    experiment_id INT NOT NULL,
                    url TEXT NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    axe_violations INT DEFAULT 0,
                    axe_critical INT DEFAULT 0,
                    axe_serious INT DEFAULT 0,
                    axe_moderate INT DEFAULT 0,
                    axe_minor INT DEFAULT 0,
                    lighthouse_score INT NULL,
                    semantic_status VARCHAR(50) NULL,
                    semantic_risk_level VARCHAR(50) NULL,
                    semantic_summary TEXT NULL,
                    semantic_findings JSON NULL,
                    html_size INT DEFAULT 0,
                    dom_nodes INT DEFAULT 0,
                    images INT DEFAULT 0,
                    images_without_alt INT DEFAULT 0,
                    links INT DEFAULT 0,
                    buttons INT DEFAULT 0,
                    forms INT DEFAULT 0,
                    inputs INT DEFAULT 0,
                    headings INT DEFAULT 0,
                    h1_count INT DEFAULT 0,
                    language_declared VARCHAR(50) NULL,
                    has_main_landmark BOOLEAN DEFAULT FALSE,
                    has_nav_landmark BOOLEAN DEFAULT FALSE,
                    has_header_landmark BOOLEAN DEFAULT FALSE,
                    has_footer_landmark BOOLEAN DEFAULT FALSE,
                    execution_seconds FLOAT NULL,
                    axe_raw_path TEXT NULL,
                    lighthouse_raw_path TEXT NULL,
                    semantic_raw_path TEXT NULL,
                    error_message TEXT NULL,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
                )
            """)

            conn.commit()
            cursor.close()
            conn.close()
            return

        except Error:
            time.sleep(2)

    raise RuntimeError("No fue posible conectar con MySQL después de varios intentos.")