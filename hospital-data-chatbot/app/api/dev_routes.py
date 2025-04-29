# app/api/dev_routes.py
from fastapi import APIRouter, Depends, Request, HTTPException
from app.config.settings import AppConfig
from app.utils.db import get_db_connection, create_tables
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

def dev_mode_only():
    """Dependency to ensure endpoint only works in development mode."""
    if not AppConfig.is_development():
        raise HTTPException(
            status_code=403, 
            detail="This endpoint is only available in development environments"
        )

@router.post("/reset-tables", dependencies=[Depends(dev_mode_only)])
async def reset_tables(request: Request):
    """
    Development-only endpoint to reset database tables.
    Drops and recreates all tables, then reloads data.
    """
    logger.warning("Reset tables endpoint called - will drop and recreate all tables")
    
    try:
        # Get data from the data processor
        patient_data = request.app.state.data_processor.patient_data
        diagnosis_data = request.app.state.data_processor.diagnosis_data
        
        if patient_data is None or diagnosis_data is None:
            raise HTTPException(
                status_code=400,
                detail="No data available. Load data before resetting tables."
            )
        
        # Get database connection
        conn = get_db_connection()
        
        try:
            # Drop and recreate tables
            create_tables(conn, patient_data, diagnosis_data, drop_if_exists=True)
            
            # Re-insert data
            from app.utils.db import insert_data
            
            # Insert patient data first (for referential integrity)
            logger.info(f"Reinserting {patient_data.height} patient records")
            patient_count = insert_data(conn, "patient_details", patient_data)
            
            # Insert diagnosis data linked to patients
            logger.info(f"Reinserting {diagnosis_data.height} diagnosis records")
            diagnosis_count = insert_data(conn, "diagnosis_details", diagnosis_data)
            
            conn.commit()
            
            return {
                "status": "success",
                "message": "Tables reset and data reloaded successfully",
                "details": {
                    "tables_dropped": ["patient_details", "diagnosis_details"],
                    "patient_records_inserted": patient_count,
                    "diagnosis_records_inserted": diagnosis_count
                }
            }
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Failed to reset tables: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset tables: {str(e)}"
        )

@router.get("/config", dependencies=[Depends(dev_mode_only)])
async def get_dev_config():
    """
    Development-only endpoint to view current configuration.
    """
    config_data = {
        "environment": AppConfig.ENV,
        "debug_mode": AppConfig.DEBUG,
        "database": {
            "host": AppConfig.DB_HOST,
            "port": AppConfig.DB_PORT,
            "name": AppConfig.DB_NAME,
            "user": AppConfig.DB_USER,
            # Password masked for security
            "password": "********" if AppConfig.DB_PASSWORD else None
        },
        "s3": {
            "enabled": AppConfig.USE_S3,
            "bucket": AppConfig.S3_BUCKET if hasattr(AppConfig, 'S3_BUCKET') else None
        },
        "bedrock": {
            "model_id": AppConfig.BEDROCK_MODEL_ID
        }
    }
    
    return config_data