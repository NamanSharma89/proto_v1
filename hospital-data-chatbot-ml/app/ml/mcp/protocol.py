# app/ml/mcp/protocol.py
from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class ModelType(str, Enum):
    READMISSION_RISK = "readmission_risk"
    PATIENT_RISK = "patient_risk"
    DIAGNOSIS_CLUSTER = "diagnosis_cluster"
    LENGTH_OF_STAY = "length_of_stay"

class ModelMetadata(BaseModel):
    """Model metadata as per MCP specification"""
    model_id: str
    version: str
    model_type: ModelType
    description: str
    created_at: str
    accuracy: float
    capabilities: List[str]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    feature_names: List[str]

class ModelContext(BaseModel):
    """Context information passed to the model"""
    patient_id: Optional[str] = None
    time_range: Optional[str] = None
    include_explanations: bool = True
    confidence_threshold: Optional[float] = None
    additional_context: Optional[Dict[str, Any]] = None

class ModelRequest(BaseModel):
    """Standard MCP request format"""
    model_id: str
    context: ModelContext
    inputs: Dict[str, Any]
    options: Optional[Dict[str, Any]] = None

class ExplanationFormat(str, Enum):
    FEATURE_IMPORTANCE = "feature_importance"
    LIME = "lime"
    SHAP = "shap"
    TEXT = "text"

class ModelExplanation(BaseModel):
    """Explanation of model prediction"""
    format: ExplanationFormat
    explanation: Any
    importance_scores: Optional[Dict[str, float]] = None

class ModelResponse(BaseModel):
    """Standard MCP response format"""
    model_id: str
    version: str
    prediction: Any
    confidence: float
    explanation: Optional[ModelExplanation] = None
    metadata: Optional[Dict[str, Any]] = None