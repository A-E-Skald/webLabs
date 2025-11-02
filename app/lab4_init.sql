-- Создание таблицы ролей
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT
);

-- Создание таблицы пользователей
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    last_name TEXT,
    first_name TEXT,
    patronymic TEXT,
    role_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- Добавляем тестовую роль
INSERT INTO roles (name, description) VALUES ('Admin', 'Администратор системы');

-- Добавляем тестового пользователя (пароль хеш: "Zalanet_514" через werkzeug)
INSERT INTO users (login, password_hash, last_name, first_name, patronymic, role_id)
VALUES ('admin', 'scrypt:32768:8:1$PuniRBOszMr3ls43$f3de290549df2da53893a326ad95f44cb2749bb2a97b02807f58ba374e2bd120f933d817e5743844a780639ba5718324b0417c93309684f50a2540499eeb58f8', 'Админов', 'Админ', 'Админович', 1);
