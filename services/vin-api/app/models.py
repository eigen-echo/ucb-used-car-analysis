from pydantic import BaseModel, Field
from typing import Optional, Any


class VINDecodeRequest(BaseModel):
    """Request model for VIN decoding."""

    vin: str = Field(
        ...,
        min_length=17,
        max_length=17,
        description="17-character Vehicle Identification Number",
        examples=["1HGBH41JXMN109186"],
    )


class VINDecodeResponse(BaseModel):
    """Response model for VIN decoding."""

    vin: str
    data: list[dict[str, Any]]
    count: int
    success: bool
    message: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    database: str
    message: str


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str
    detail: Optional[str] = None
