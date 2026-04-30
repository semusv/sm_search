from common.repository import RetrievedChunk
from common.search_pipeline import SearchPipeline


def test_merge_and_deduplicate_prefers_higher_score() -> None:
    reranked = [
        RetrievedChunk("SAP-1", 0, "a", "FI", 0.9, "reranked"),
        RetrievedChunk("SAP-2", 0, "b", "MM", 0.7, "reranked"),
    ]
    fuzzy = [
        RetrievedChunk("SAP-1", 0, "a", "FI", 0.8, "fuzzy"),
        RetrievedChunk("SAP-3", 0, "c", "SD", 0.6, "fuzzy"),
    ]

    merged = SearchPipeline._merge_and_deduplicate(reranked, fuzzy)
    assert len(merged) == 3
    assert merged[0].ticket_id == "SAP-1"
    assert merged[0].score == 0.9
