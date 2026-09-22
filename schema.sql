-- ==========================================================
-- Скрипт схемы базы данных для PostgreSQL 16
-- Система регистрации обращений граждан
-- ==========================================================

-- Удаление существующих таблиц, если они уже имеются
DROP TABLE IF EXISTS appeals CASCADE;
DROP TABLE IF EXISTS management_plots CASCADE;
DROP TABLE IF EXISTS management_districts CASCADE;
DROP TABLE IF EXISTS results CASCADE;
DROP TABLE IF EXISTS topics CASCADE;
DROP TABLE IF EXISTS appeal_types CASCADE;
DROP TABLE IF EXISTS plots CASCADE;
DROP TABLE IF EXISTS managements CASCADE;
DROP TABLE IF EXISTS districts CASCADE;
DROP TABLE IF EXISTS sources CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. Таблица пользователей
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    full_name VARCHAR(128) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'registrator',
    is_builtin BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_users_username ON users (username);

-- 2. Справочник: Источники поступления
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) UNIQUE NOT NULL,
    code VARCHAR(32),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 3. Справочник: Округа
CREATE TABLE districts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) UNIQUE NOT NULL,
    code VARCHAR(32),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 4. Справочник: Управления
CREATE TABLE managements (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) UNIQUE NOT NULL,
    code VARCHAR(32),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 5. Справочник: Участки
CREATE TABLE plots (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) UNIQUE NOT NULL,
    code VARCHAR(32),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 6. Справочник: Типы обращений
CREATE TABLE appeal_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) UNIQUE NOT NULL,
    code VARCHAR(32),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 7. Справочник: Тематики обращений
CREATE TABLE topics (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) UNIQUE NOT NULL,
    code VARCHAR(32),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 8. Справочник: Результаты рассмотрения
CREATE TABLE results (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) UNIQUE NOT NULL,
    code VARCHAR(32),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 9. Таблица связей: Управление <-> Округа (в управление может входить несколько округов)
CREATE TABLE management_districts (
    management_id INTEGER NOT NULL REFERENCES managements(id) ON DELETE CASCADE,
    district_id INTEGER NOT NULL REFERENCES districts(id) ON DELETE CASCADE,
    PRIMARY KEY (management_id, district_id)
);

-- 10. Таблица связей: Управление <-> Участки (в управление может входить несколько участков)
CREATE TABLE management_plots (
    management_id INTEGER NOT NULL REFERENCES managements(id) ON DELETE CASCADE,
    plot_id INTEGER NOT NULL REFERENCES plots(id) ON DELETE CASCADE,
    PRIMARY KEY (management_id, plot_id)
);

-- 11. Основная таблица: Обращения граждан
CREATE TABLE appeals (
    id SERIAL PRIMARY KEY,
    number VARCHAR(100) NOT NULL,
    reg_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'В работе',
    
    source_id INTEGER NOT NULL REFERENCES sources(id),
    district_id INTEGER NOT NULL REFERENCES districts(id),
    management_id INTEGER REFERENCES managements(id) ON DELETE SET NULL,
    plot_id INTEGER REFERENCES plots(id) ON DELETE SET NULL,
    
    applicant_gender VARCHAR(20),
    appeal_type_id INTEGER NOT NULL REFERENCES appeal_types(id),
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    validity VARCHAR(50),
    recurrence VARCHAR(50),
    result_id INTEGER REFERENCES results(id) ON DELETE SET NULL,
    
    deadline_date DATE,
    not_serviced BOOLEAN NOT NULL DEFAULT FALSE,
    comment TEXT,
    
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    created_by_id INTEGER NOT NULL REFERENCES users(id),
    closed_at TIMESTAMP WITHOUT TIME ZONE,
    closed_by_id INTEGER REFERENCES users(id)
);

-- Индексы для ускорения поиска и фильтрации
CREATE INDEX ix_appeals_number ON appeals (number);
CREATE INDEX ix_appeals_reg_date ON appeals (reg_date);
CREATE INDEX ix_appeals_status ON appeals (status);
CREATE INDEX ix_appeals_deadline_date ON appeals (deadline_date);
