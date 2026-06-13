# app/core/exceptions.py
from fastapi import HTTPException, status

class DataNotFoundException(HTTPException):
    def __init__(self, detail: str = "Requested data not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class ReportGenerationException(HTTPException):
    def __init__(self, detail: str = "Failed to generate report"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)