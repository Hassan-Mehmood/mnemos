from typing import List

from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
    return _model


class LongTermSemanticMemory:
    instance: "LongTermSemanticMemory | None" = None
    model: SentenceTransformer

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
            cls.instance.model = _get_model()
        return cls.instance

    def create_embeddings(self, texts: List[str], is_query: bool = False):
        if is_query:
            texts = [
                f"Instruct: Given a user query, retrieve relevant personal facts\nQuery: {t}"
                for t in texts
            ]
        return self.model.encode(texts)

    def compute_similarity(self, query_embeddings, document_embeddings):
        return self.model.similarity(query_embeddings, document_embeddings)
