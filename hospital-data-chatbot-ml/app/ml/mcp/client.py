# app/ml/mcp/client.py
import requests
from typing import Dict, List, Any, Optional
from app.ml.mcp.protocol import (
    ModelRequest, ModelResponse, ModelContext, 
    ModelMetadata, ModelType
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

class MCPClient:
    """Client for interacting with MCP-compliant ML API."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        
    def get_models(self) -> List[ModelMetadata]:
        """Get list of available models."""
        url = f"{self.base_url}/models"
        headers = self._get_headers()
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            self._handle_error(response)
        
        return [ModelMetadata(**model) for model in response.json()]
    
    def get_model_metadata(self, model_id: str) -> ModelMetadata:
        """Get metadata for a specific model."""
        url = f"{self.base_url}/models/{model_id}"
        headers = self._get_headers()
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            self._handle_error(response)
        
        return ModelMetadata(**response.json())
    
    def predict(self, request: ModelRequest) -> ModelResponse:
        """Make a prediction using the Model Context Protocol."""
        url = f"{self.base_url}/predict"
        headers = self._get_headers()
        
        response = requests.post(url, headers=headers, json=request.dict())
        if response.status_code != 200:
            self._handle_error(response)
        
        return ModelResponse(**response.json())
    
    def predict_readmission_risk(self, patient_id: str, include_explanations: bool = True) -> ModelResponse:
        """Helper method to predict readmission risk for a patient."""
        request = ModelRequest(
            model_id="readmission-risk-xgboost-v1",
            context=ModelContext(
                patient_id=patient_id,
                include_explanations=include_explanations
            ),
            inputs={"patient_id": patient_id}
        )
        
        return self.predict(request)
    
    def predict_patient_risk(self, patient_id: str, include_explanations: bool = True) -> ModelResponse:
        """Helper method to predict risk stratification for a patient."""
        request = ModelRequest(
            model_id="patient-risk-xgboost-v1",
            context=ModelContext(
                patient_id=patient_id,
                include_explanations=include_explanations
            ),
            inputs={"patient_id": patient_id}
        )
        
        return self.predict(request)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _handle_error(self, response):
        """Handle error responses from the API."""
        try:
            error_msg = response.json().get("detail", f"HTTP error {response.status_code}")
        except:
            error_msg = f"HTTP error {response.status_code}: {response.text}"
        
        logger.error(f"ML API error: {error_msg}")
        raise ValueError(f"ML API error: {error_msg}")