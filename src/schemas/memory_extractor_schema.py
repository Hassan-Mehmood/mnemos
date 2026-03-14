from pydantic import BaseModel, Field


class ExtractorOutput(BaseModel):
    key: str = Field(..., description="The key of the memory")
    value: str = Field(..., description="The value of the memory")
    confidence: float = Field(
        le=10, ge=0, description="The confidence score of the key and value"
    )
