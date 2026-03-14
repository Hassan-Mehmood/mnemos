# from typing import List
# from pydantic import BaseModel

import uuid

from src.schemas.memory_extractor_schema import ExtractorOutput


class UserMemories(ExtractorOutput):
    superseded_by: uuid.UUID | None = None
