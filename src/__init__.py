from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.chats.chat_router import router as chat_router
from src.core.database.database import sessionmanager
from src.memory.long_term_memory import LongTermSemanticMemory


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Function that handles startup and shutdown events.
    """
    LongTermSemanticMemory()
    yield
    if sessionmanager._engine is not None:
        # Close the DB connection
        await sessionmanager.close()


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:8081",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/health")
def root():
    return {"message": "Ok"}


@app.get("/embeddings")
def get_embeddings():
    # Requires transformers>=4.51.0
    # Requires sentence-transformers>=2.7.0

    from sentence_transformers import SentenceTransformer

    # Load the model
    model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")

    # We recommend enabling flash_attention_2 for better acceleration and memory saving,
    # together with setting `padding_side` to "left":
    # model = SentenceTransformer(
    #     "Qwen/Qwen3-Embedding-0.6B",
    #     model_kwargs={"attn_implementation": "flash_attention_2", "device_map": "auto"},
    #     tokenizer_kwargs={"padding_side": "left"},
    # )

    # The queries and documents to embed
    queries = [
        "What is the capital of China?",
        "Explain gravity",
    ]
    documents = [
        "The capital of China is Beijing.",
        "Gravity is a force that attracts two bodies towards each other. It gives weight to physical objects and is responsible for the movement of planets around the sun.",
    ]

    # Encode the queries and documents. Note that queries benefit from using a prompt
    # Here we use the prompt called "query" stored under `model.prompts`, but you can
    # also pass your own prompt via the `prompt` argument
    query_embeddings = model.encode(queries, prompt_name="query")
    document_embeddings = model.encode(documents)

    # Compute the (cosine) similarity between the query and document embeddings
    similarity = model.similarity(query_embeddings, document_embeddings)
    print(similarity)
    # tensor([[0.7646, 0.1414],
    #         [0.1355, 0.6000]])
