-- Пример загрузки данных во внешнюю таблицу-источник.
-- Используйте этот формат для ETL/стороннего загрузчика.

INSERT INTO public.tickets_source (ticket_id, user_question, support_answer, functional_area)
VALUES
    (
        'SAP-12345',
        'Ошибка при создании заказа в MM.',
        'Проверьте тип документа, настройку релиз-стратегии и обязательные поля.',
        'MM'
    ),
    (
        'SAP-67890',
        'Не проходит проводка в FI.',
        'Проверьте период проводки и статус блокировки счета.',
        'FI'
    )
ON CONFLICT (ticket_id) DO UPDATE
SET
    user_question = EXCLUDED.user_question,
    support_answer = EXCLUDED.support_answer,
    functional_area = EXCLUDED.functional_area;
