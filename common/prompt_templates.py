from common.repository import RetrievedChunk


def build_answer_prompt(user_query: str, chunks: list[RetrievedChunk]) -> str:
    header = (
        "Ты — эксперт по системе SAP. На основе следующих фрагментов из базы знаний "
        "(обращений в поддержку) ответь на вопрос пользователя. Если информации "
        "недостаточно, скажи честно. Приведи ссылки на номера обращений (ticket_id), "
        "если они есть.\n\n"
        f"Вопрос: {user_query}\n\n"
        "Контекст:\n"
    )
    parts: list[str] = [header]
    for chunk in chunks:
        parts.append(
            f"--- Обращение {chunk.ticket_id} "
            f"(функциональная область {chunk.functional_area or 'n/a'}, чанк {chunk.chunk_index}) ---\n"
            f"{chunk.chunk_text}\n"
        )
    parts.append("\nОтвет:\n")
    return "\n".join(parts)
