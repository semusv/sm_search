-- Шаблон внешней таблицы-источника для /index-from-source.
-- При необходимости замените имена схемы/таблицы под ваш контур.

CREATE SCHEMA IF NOT EXISTS public;

CREATE TABLE IF NOT EXISTS public.tickets_source (
    ticket_id TEXT PRIMARY KEY,
    user_question TEXT NOT NULL,
    support_answer TEXT NOT NULL,
    functional_area TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Индексы для быстрого чтения и фильтрации.
CREATE INDEX IF NOT EXISTS idx_tickets_source_functional_area
    ON public.tickets_source (functional_area);

CREATE INDEX IF NOT EXISTS idx_tickets_source_created_at
    ON public.tickets_source (created_at);
