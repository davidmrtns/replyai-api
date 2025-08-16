from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions.exceptions import AppException
from app.utils.logger import logger


async def exception_handler(request: Request, exc: AppException):
    logger.error(exc, exc_info=True)
    logger.error(f"Detailed data: {exc.detailed()}")
    
    return JSONResponse(
        status_code=exc.http_status_code,
        content={"message": exc.user_friendly_detail}
    )


# TODO: add generic exception handler for other exceptions
