from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class BaseQueryParams(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat()},
    )


class PaginationMeta(BaseSchema):
    page: int = Field(ge=1, description="Current page number")
    limit: int = Field(ge=1, le=100, description="Items per page")
    total: int = Field(ge=0, description="Total items matching filters")
    total_unfiltered: int | None = Field(
        default=None, ge=0, description="Total items without filters"
    )
    total_pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_prev: bool = Field(description="Whether there is a previous page")


class PaginatedResponse(BaseSchema, Generic[T]):
    message: str = Field(description="Message of the response")
    data: list[T] = Field(description="Data of the response")
    pagination: PaginationMeta = Field(description="Pagination of the response")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    success: bool = Field(default=False, description="Success of the response")
    error: ErrorDetail = Field(description="Error of the response")


class SuccessResponse(BaseSchema, Generic[T]):
    success: bool = Field(default=True, description="Success of the response")
    message: str = Field(description="Message of the response")
    data: T = Field(description="Data of the response")
