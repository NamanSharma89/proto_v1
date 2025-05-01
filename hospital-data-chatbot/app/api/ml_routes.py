# app/api/ml_routes.py
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from app.ml.hospital_ml_models import HospitalMLModels
from app.ml.sagemaker_integration import SageMakerIntegration
from app.config.settings import AppConfig
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

class ModelTrainingRequest(BaseModel):
    """Model for a machine learning model training request."""
    model_name: str
    feature_set_name: str
    target_column: str
    hyperparameters: Optional[Dict[str, str]] = None
    instance_type: str = "ml.m5.large"

class ModelDeployRequest(BaseModel):
    """Model for a machine learning model deployment request."""
    training_job_name: str
    instance_type: str = "ml.t2.medium"

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
        # Initialize ML models helper
        if not hasattr(request.app.state, "ml_models"):
            logger.info("Initializing Hospital ML Models")
            request.app.state.ml_models = HospitalMLModels()
        
        ml_models = request.app.state.ml_models
        
        # Get risk stratification
        result = ml_models.get_patient_risk_stratification(patient_id)
        
        if result.get('status') == 'error':
            raise HTTPException(
                status_code=404, 
                detail=result.get('message', 'Patient not found or error getting risk data')
            )
        
        return result
    
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
        # Initialize ML models helper
        if not hasattr(request.app.state, "ml_models"):
            logger.info("Initializing Hospital ML Models")
            request.app.state.ml_models = HospitalMLModels()
        
        ml_models = request.app.state.ml_models
        
        # Get readmission risk
        result = ml_models.get_readmission_risk(patient_id)
        
        if result.get('status') == 'error':
            raise HTTPException(
                status_code=404, 
                detail=result.get('message', 'Patient not found or error getting risk data')
            )
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting readmission risk: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get readmission risk: {str(e)}"
        )

@router.get("/diagnosis-clusters")
async def get_diagnosis_clusters(
    request: Request, 
    min_cluster_size: int = Query(5, description="Minimum number of diagnoses in a cluster")
):
    """
    Get clusters of similar diagnoses based on pattern analysis.
    """
    try:
        # Initialize ML models helper
        if not hasattr(request.app.state, "ml_models"):
            logger.info("Initializing Hospital ML Models")
            request.app.state.ml_models = HospitalMLModels()
        
        ml_models = request.app.state.ml_models
        
        # Get diagnosis clusters
        result = ml_models.get_diagnosis_clusters(min_cluster_size)
        
        if result.get('status') == 'error':
            raise HTTPException(
                status_code=500, 
                detail=result.get('message', 'Error getting diagnosis clusters')
            )
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting diagnosis clusters: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get diagnosis clusters: {str(e)}"
        )

@router.post("/train-model")
async def train_model(request: Request, training_request: ModelTrainingRequest):
    """
    Train a new machine learning model using SageMaker.
    Only available in development and staging environments.
    """
    # Security check - not available in production
    if AppConfig.is_production():
        raise HTTPException(
            status_code=403,
            detail="Model training is not available in production environment"
        )
    
    try:
        # Initialize SageMaker integration
        if not hasattr(request.app.state, "sagemaker"):
            logger.info("Initializing SageMaker Integration")
            request.app.state.sagemaker = SageMakerIntegration()
        
        sagemaker = request.app.state.sagemaker
        
        # Train model
        result = sagemaker.train_model(
            model_name=training_request.model_name,
            feature_set_name=training_request.feature_set_name,
            target_column=training_request.target_column,
            instance_type=training_request.instance_type,
            hyperparameters=training_request.hyperparameters
        )
        
        return {
            "status": "success",
            "message": "Model training job started",
            "details": result
        }
        
    except Exception as e:
        logger.error(f"Error starting model training: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start model training: {str(e)}"
        )

@router.post("/deploy-model")
async def deploy_model(request: Request, deploy_request: ModelDeployRequest):
    """
    Deploy a trained machine learning model to a SageMaker endpoint.
    Only available in development and staging environments.
    """
    # Security check - not available in production
    if AppConfig.is_production():
        raise HTTPException(
            status_code=403,
            detail="Model deployment is not available in production environment"
        )
    
    try:
        # Initialize SageMaker integration
        if not hasattr(request.app.state, "sagemaker"):
            logger.info("Initializing SageMaker Integration")
            request.app.state.sagemaker = SageMakerIntegration()
        
        sagemaker = request.app.state.sagemaker
        
        # Deploy model
        result = sagemaker.deploy_model(
            training_job_name=deploy_request.training_job_name,
            instance_type=deploy_request.instance_type
        )
        
        return {
            "status": "success",
            "message": "Model deployment initiated",
            "details": result
        }
        
    except Exception as e:
        logger.error(f"Error deploying model: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deploy model: {str(e)}"
        )