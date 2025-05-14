# app/api/ml_routes.py
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from app.ml.mcp.client import MCPClient
from app.ml.mcp.protocol import ModelContext
from app.config.settings import AppConfig
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Update with environment-specific ML API URL
ML_API_URL = AppConfig.ML_API_URL
ML_API_KEY = AppConfig.ML_API_KEY

@router.get("/patient-risk")
async def get_patient_risk(
    request: Request, 
    patient_id: Optional[str] = Query(None, description="Patient registry ID. If not provided, returns risk for all patients")
):
    """
    Get risk stratification for patients.
    If patient_id is provided, returns risk for that specific patient.
    Otherwise, returns population-level risk statistics.
    """
    try:
        # Initialize MCP client if not in app state
        if not hasattr(request.app.state, "mcp_client"):
            logger.info("Initializing MCP client")
            request.app.state.mcp_client = MCPClient(ML_API_URL, ML_API_KEY)
        
        mcp_client = request.app.state.mcp_client
        
        if patient_id:
            # Get risk for specific patient using MCP
            response = mcp_client.predict_patient_risk(patient_id)
            return response.prediction
        else:
            # For population-level risk, we'll use the existing implementation
            # Initialize ML models helper
            if not hasattr(request.app.state, "ml_models"):
                logger.info("Initializing Hospital ML Models")
                request.app.state.ml_models = HospitalMLModels()
            
            ml_models = request.app.state.ml_models
            result = ml_models.get_patient_risk_stratification()
            
            if result.get('status') == 'error':
                raise HTTPException(
                    status_code=404, 
                    detail=result.get('message', 'Error getting population risk data')
                )
            
            return result
    
    except ValueError as e:
        logger.error(f"Error getting patient risk: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting patient risk: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get patient risk: {str(e)}"
        )

@router.get("/readmission-risk/{patient_id}")
async def get_readmission_risk(request: Request, patient_id: str):
    """
    Get 30-day readmission risk prediction for a specific patient.
    """
    try:
        # Initialize MCP client if not in app state
        if not hasattr(request.app.state, "mcp_client"):
            logger.info("Initializing MCP client")
            request.app.state.mcp_client = MCPClient(ML_API_URL, ML_API_KEY)
        
        mcp_client = request.app.state.mcp_client
        
        # Get readmission risk using MCP
        response = mcp_client.predict_readmission_risk(patient_id)
        
        # Return the prediction part of the response
        return response.prediction
    
    except ValueError as e:
        logger.error(f"Error getting readmission risk: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting readmission risk: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get readmission risk: {str(e)}"
        )

# app/api/routes.py (updated)

@router.post("/analyze-patient")
async def analyze_patient(request: Request, patient_id: str):
    """
    Analyze patient data using ML models through MCP.
    Returns comprehensive analysis including risk factors and predictions.
    """
    try:
        # Initialize MCP client if not in app state
        if not hasattr(request.app.state, "mcp_client"):
            logger.info("Initializing MCP client")
            request.app.state.mcp_client = MCPClient(AppConfig.ML_API_URL, AppConfig.ML_API_KEY)
        
        mcp_client = request.app.state.mcp_client
        
        # Get patient data
        from app.utils.db import get_db_connection
        import polars as pl
        
        conn = get_db_connection()
        query = f"""
        SELECT * FROM patient_details 
        WHERE registry_id = '{patient_id}'
        """
        patient_df = pl.read_database(query=query, connection=conn)
        
        if patient_df.height == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Patient {patient_id} not found"
            )
        
        # Get patient diagnoses
        query = f"""
        SELECT * FROM diagnosis_details 
        WHERE registry_id = '{patient_id}'
        """
        diagnosis_df = pl.read_database(query=query, connection=conn)
        
        # Get predictions through MCP
        readmission_response = mcp_client.predict_readmission_risk(patient_id)
        risk_response = mcp_client.predict_patient_risk(patient_id)
        
        # Combine results
        result = {
            "patient": patient_df.to_dicts()[0],
            "diagnoses": diagnosis_df.to_dicts(),
            "readmission_risk": readmission_response.prediction,
            "risk_stratification": risk_response.prediction,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing patient: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze patient: {str(e)}"
        )