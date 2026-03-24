from typing import List

from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
    return _model


class LongTermSemanticMemory:
    def __init__(self):
        self.model = _get_model()
        # We recommend enabling flash_attention_2 for better acceleration and memory saving,
        # together with setting `padding_side` to "left":
        # model = SentenceTransformer(
        #     "Qwen/Qwen3-Embedding-0.6B",
        #     model_kwargs={"attn_implementation": "flash_attention_2", "device_map": "auto"},
        #     tokenizer_kwargs={"padding_side": "left"},
        # )

    def create_embeddings(self, texts: List[str], is_query: bool = False):
        prompt_name = "query" if is_query else None
        return self.model.encode(texts, prompt_name=prompt_name)

    def compute_similarity(self, query_embeddings, document_embeddings):
        return self.model.similarity(query_embeddings, document_embeddings)
