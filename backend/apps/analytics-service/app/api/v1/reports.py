from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
import logging

from app.api.dependencies import get_db
from app.schemas.report import ReportRequest
from app.services.reporting import generate_csv_report

logger = logging.getLogger("omnisight.analytics.reports")

router = APIRouter(prefix="/reports", tags=["Reporting"])

@router.post("/generate")
def generate_report(request: ReportRequest, db: Session = Depends(get_db)):
    try:
        # request.report_type.value extracts the string from the Enum
        report_name = request.report_type.value
        logger.info(f"Generating {report_name} report from {request.date_from} to {request.date_to}")
        
        csv_data = generate_csv_report(
            db=db, 
            report_type=report_name, 
            start_date=request.date_from, 
            end_date=request.date_to
        )
        
        # Return proper file response
        return Response(
            content=csv_data, 
            media_type="text/csv", 
            headers={"Content-Disposition": f'attachment; filename="{report_name}_report.csv"'}
        )
        
    except ValueError as e:
        logger.warning(f"Invalid report request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Report generation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")