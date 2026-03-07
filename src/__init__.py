from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.chats.router import router as chat_router
from src.database.database import sessionmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Function that handles startup and shutdown events.
    """
    yield
    if sessionmanager._engine is not None:
        # Close the DB connection
        await sessionmanager.close()


app = FastAPI(lifespan=lifespan)


app.include_router(chat_router)


@app.get("/health")
def root():
    return {"message": "Ok"}
