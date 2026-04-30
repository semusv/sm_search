-- Полностью параметризуемый шаблон внешней таблицы-источника.
-- Перед применением замените плейсхолдеры:
--   {{SCHEMA}}  -> имя схемы
--   {{TABLE}}   -> имя таблицы

CREATE SCHEMA IF NOT EXISTS {{SCHEMA}};

CREATE TABLE IF NOT EXISTS {{SCHEMA}}.{{TABLE}} (
    ticket_id TEXT PRIMARY KEY,
    user_question TEXT NOT NULL,
    support_answer TEXT NOT NULL,
    functional_area TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Индексы для фильтрации и инкрементальной обработки.
CREATE INDEX IF NOT EXISTS idx_{{TABLE}}_functional_area
    ON {{SCHEMA}}.{{TABLE}} (functional_area);

CREATE INDEX IF NOT EXISTS idx_{{TABLE}}_created_at
    ON {{SCHEMA}}.{{TABLE}} (created_at);
