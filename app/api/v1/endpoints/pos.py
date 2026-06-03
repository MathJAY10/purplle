from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form

from app.core.dependencies import get_pos_ingestion_service
from app.services.pos_ingestion import POSIngestionService

router = APIRouter(prefix="/pos", tags=["pos"])

@router.post("/transactions/upload")
async def upload_pos_transactions(
    file: UploadFile = File(...),
    store_timezone: str = Form("UTC"),
    service: POSIngestionService = Depends(get_pos_ingestion_service)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
        
    result = await service.ingest_csv(file.file, store_timezone=store_timezone)
    
    return {
        "status": "success",
        "message": f"Ingested {result['parsed']} transactions.",
        "errors": result['errors']
    }
