from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from models import (
    VINDecodeRequest,
    VINDecodeResponse,
    HealthResponse,
    ErrorResponse,
)
from database import execute_query, test_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="NHTSA vPIC VIN Decoder API",
    description="RESTful API for decoding Vehicle Identification Numbers using NHTSA vPIC database",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "NHTSA vPIC VIN Decoder API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "decode_vin_get": "/decode/{vin}",
            "decode_vin_post": "/decode",
            "docs": "/docs",
            "redoc": "/redoc",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify API and database status.
    """
    db_status = "connected" if test_connection() else "disconnected"

    if db_status == "disconnected":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": db_status,
                "message": "Database connection failed",
            },
        )

    return HealthResponse(
        status="healthy",
        database=db_status,
        message="API is running and database is accessible",
    )


@app.get(
    "/decode/{vin}",
    response_model=VINDecodeResponse,
    tags=["VIN Decode"],
    responses={
        200: {"description": "VIN decoded successfully"},
        400: {"model": ErrorResponse, "description": "Invalid VIN format"},
        500: {"model": ErrorResponse, "description": "Database error"},
    },
)
async def decode_vin_get(vin: str):
    """
    Decode a VIN using GET request.

    Args:
        vin: 17-character Vehicle Identification Number

    Returns:
        VINDecodeResponse with decoded vehicle information
    """
    return await _decode_vin(vin)


@app.post(
    "/decode",
    response_model=VINDecodeResponse,
    tags=["VIN Decode"],
    responses={
        200: {"description": "VIN decoded successfully"},
        400: {"model": ErrorResponse, "description": "Invalid VIN format"},
        500: {"model": ErrorResponse, "description": "Database error"},
    },
)
async def decode_vin_post(request: VINDecodeRequest):
    """
    Decode a VIN using POST request.

    Args:
        request: VINDecodeRequest containing the VIN

    Returns:
        VINDecodeResponse with decoded vehicle information
    """
    return await _decode_vin(request.vin)


async def _decode_vin(vin: str) -> VINDecodeResponse:
    """
    Internal function to decode VIN.

    Args:
        vin: 17-character Vehicle Identification Number

    Returns:
        VINDecodeResponse with decoded vehicle information

    Raises:
        HTTPException: If VIN is invalid or database error occurs
    """
    # Validate VIN length
    vin = vin.strip().upper()
    if len(vin) != 17:
        logger.warning(f"Invalid VIN length: {len(vin)} characters")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"VIN must be exactly 17 characters. Received {len(vin)} characters.",
        )

    try:
        logger.info(f"Decoding VIN: {vin}")

        # Call the stored procedure
        query = "SELECT * FROM vpic.spVinDecode(%s)"
        results = execute_query(query, (vin,))

        logger.info(f"VIN decode returned {len(results)} records")

        return VINDecodeResponse(
            vin=vin,
            data=results,
            count=len(results),
            success=True,
            message="VIN decoded successfully",
        )

    except Exception as e:
        logger.error(f"Error decoding VIN {vin}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
