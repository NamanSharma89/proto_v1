# app/ml/mcp/service.py
from fastapi import FastAPI, HTTPException, Depends
from app.ml.mcp.protocol import (
    ModelRequest, ModelResponse, ModelType, 
    ModelMetadata, ModelExplanation, ExplanationFormat
)
from app.ml.sagemaker_integration import SageMakerIntegration
from app.ml.feature_store import FeatureStore
from app.utils.logging import get_logger
from typing import Dict, List, Any, Optional
import time
import json

logger = get_logger(__name__)

class MCPModelService:
    """Model Context Protocol service for hospital ML models"""
    
    def __init__(self):
        self.sagemaker = SageMakerIntegration()
        self.feature_store = FeatureStore()
        self.model_registry = self._load_model_registry()
        
    def _load_model_registry(self) -> Dict[str, ModelMetadata]:
        """Load model registry with all available models"""
        # This would normally load from a database or model registry
        # For now, we'll hard-code a few examples
        registry = {}
        
        # Readmission risk model
        registry["readmission-risk-xgboost-v1"] = ModelMetadata(
            model_id="readmission-risk-xgboost-v1",
            version="1.0.0",
            model_type=ModelType.READMISSION_RISK,
            description="XGBoost model for 30-day readmission risk prediction",
            created_at="2025-05-01T10:00:00Z",
            accuracy=0.82,
            capabilities=["prediction", "explanation", "feature_importance"],
            input_schema={"patient_id": "string"},
            output_schema={
                "risk_score": "float",
                "risk_level": "string",
                "risk_factors": "array"
            },
            feature_names=[
                "age", "gender", "stay_duration", "diagnosis_count",
                "has_diabetes", "has_hypertension", "has_heart_condition",
                "comorbidity_score"
            ]
        )
        
        # Patient risk stratification model
        registry["patient-risk-xgboost-v1"] = ModelMetadata(
            model_id="patient-risk-xgboost-v1",
            version="1.0.0",
            model_type=ModelType.PATIENT_RISK,
            description="XGBoost model for patient risk stratification",
            created_at="2025-04-15T14:30:00Z",
            accuracy=0.79,
            capabilities=["prediction", "explanation", "feature_importance"],
            input_schema={"patient_id": "string"},
            output_schema={
                "risk_score": "float",
                "risk_level": "string"
            },
            feature_names=[
                "age", "gender", "stay_duration", "diagnosis_count",
                "has_diabetes", "has_hypertension", "has_heart_condition",
                "comorbidity_score"
            ]
        )
        
        return registry
    
    def get_models(self) -> List[ModelMetadata]:
        """Get list of all available models"""
        return list(self.model_registry.values())
    
    def get_model_metadata(self, model_id: str) -> ModelMetadata:
        """Get metadata for a specific model"""
        if model_id not in self.model_registry:
            raise ValueError(f"Model {model_id} not found")
        return self.model_registry[model_id]
    
    def predict(self, request: ModelRequest) -> ModelResponse:
        """Make a prediction using the MCP protocol"""
        start_time = time.time()
        
        # Validate model exists
        if request.model_id not in self.model_registry:
            raise ValueError(f"Model {request.model_id} not found")
        
        model_metadata = self.model_registry[request.model_id]
        model_type = model_metadata.model_type
        
        # Route to appropriate prediction function based on model type
        if model_type == ModelType.READMISSION_RISK:
            result = self._predict_readmission_risk(request)
        elif model_type == ModelType.PATIENT_RISK:
            result = self._predict_patient_risk(request)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        # Log performance
        execution_time = time.time() - start_time
        logger.info(f"Model {request.model_id} prediction completed in {execution_time:.2f}s")
        
        return result
    
    def _predict_readmission_risk(self, request: ModelRequest) -> ModelResponse:
        """Predict readmission risk using SageMaker endpoint"""
        patient_id = request.context.patient_id
        if not patient_id:
            if "patient_id" in request.inputs:
                patient_id = request.inputs["patient_id"]
            else:
                raise ValueError("Patient ID not provided in context or inputs")
        
        # Get patient features from feature store
        features = self.feature_store.get_features_for_entity(
            "readmission_prediction", patient_id
        )
        
        if not features:
            raise ValueError(f"No features found for patient {patient_id}")
        
        # Get endpoint name based on model ID
        endpoint_name = self._get_endpoint_name(request.model_id)
        
        # Get prediction from SageMaker endpoint
        sagemaker_response = self.sagemaker.get_prediction(endpoint_name, features)
        prediction_result = sagemaker_response.get("prediction", {})
        
        # Extract risk score from response
        risk_score = prediction_result.get("score", 0.0)
        
        # Determine risk level based on score
        risk_level = "Low"
        if risk_score >= 0.7:
            risk_level = "High"
        elif risk_score >= 0.3:
            risk_level = "Medium"
        
        # Generate explanation if requested
        explanation = None
        if request.context.include_explanations:
            feature_importance = self._get_feature_importance(
                request.model_id, 
                features, 
                prediction_result
            )
            explanation = ModelExplanation(
                format=ExplanationFormat.FEATURE_IMPORTANCE,
                explanation="Key factors contributing to readmission risk",
                importance_scores=feature_importance
            )
        
        # Construct MCP response
        response = ModelResponse(
            model_id=request.model_id,
            version=self.model_registry[request.model_id].version,
            prediction={
                "risk_score": risk_score,
                "risk_percentage": round(risk_score * 100, 1),
                "risk_level": risk_level,
                "patient_id": patient_id,
                "key_factors": self._get_key_risk_factors(features, feature_importance if explanation else None)
            },
            confidence=prediction_result.get("confidence", 0.8),
            explanation=explanation,
            metadata={
                "inference_time_ms": prediction_result.get("inference_time_ms", 0),
                "model_type": ModelType.READMISSION_RISK.value
            }
        )
        
        return response
    
    def _predict_patient_risk(self, request: ModelRequest) -> ModelResponse:
        """Predict patient risk using SageMaker endpoint"""
        # Implementation similar to _predict_readmission_risk
        # but for patient risk stratification model
        pass
    
    def _get_endpoint_name(self, model_id: str) -> str:
        """Get SageMaker endpoint name for model ID"""
        # This would typically come from a model registry or database
        # For now, use a simple mapping
        endpoint_mapping = {
            "readmission-risk-xgboost-v1": "hospital-data-chatbot-dev-readmission-endpoint",
            "patient-risk-xgboost-v1": "hospital-data-chatbot-dev-patient-risk-endpoint"
        }
        
        if model_id not in endpoint_mapping:
            raise ValueError(f"No endpoint found for model {model_id}")
        
        return endpoint_mapping[model_id]
    
    def _get_feature_importance(
        self, model_id: str, features: Dict[str, Any], prediction_result: Dict[str, Any]
    ) -> Dict[str, float]:
        """Get feature importance scores"""
        # This would typically come from the model explanation
        # For XGBoost models, we'd use SHAP values
        # For now, return dummy values
        feature_importance = {}
        
        # Use any feature importance from SageMaker response
        if "feature_importance" in prediction_result:
            return prediction_result["feature_importance"]
        
        # Otherwise generate some dummy values
        metadata = self.model_registry[model_id]
        for feature in metadata.feature_names:
            if feature in features:
                # Random importance score between 0 and 1
                import random
                feature_importance[feature] = random.random()
        
        # Normalize to sum to 1
        total = sum(feature_importance.values())
        if total > 0:
            feature_importance = {k: v/total for k, v in feature_importance.items()}
        
        return feature_importance
    
    def _get_key_risk_factors(
        self, patient_features: Dict[str, Any], feature_importance: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """Extract key risk factors from patient features and importance scores"""
        risk_factors = []
        
        # Use feature importance to rank factors if available
        if feature_importance:
            # Sort features by importance
            sorted_features = sorted(
                feature_importance.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            # Take top 5 features
            for feature, importance in sorted_features[:5]:
                if feature in patient_features:
                    value = patient_features[feature]
                    impact = "high" if importance > 0.3 else "medium" if importance > 0.1 else "low"
                    
                    # Format the factor based on feature type
                    if feature == "age":
                        risk_factors.append({
                            "factor": "Age",
                            "value": f"{value} years",
                            "impact": impact
                        })
                    elif feature == "comorbidity_score":
                        risk_factors.append({
                            "factor": "Comorbidity Score",
                            "value": str(value),
                            "impact": impact
                        })
                    elif feature.startswith("has_") and value == 1:
                        # Convert has_diabetes to Diabetes
                        condition = feature[4:].replace("_", " ").title()
                        risk_factors.append({
                            "factor": condition,
                            "value": "Present",
                            "impact": impact
                        })
                    elif feature == "stay_duration":
                        risk_factors.append({
                            "factor": "Previous Stay Duration",
                            "value": f"{value} days",
                            "impact": impact
                        })
        else:
            # Without feature importance, use domain knowledge
            if patient_features.get("age", 0) >= 65:
                risk_factors.append({
                    "factor": "Advanced Age",
                    "value": f"{patient_features['age']} years",
                    "impact": "high" if patient_features.get("age", 0) >= 75 else "medium"
                })
                
            # Check comorbidities
            comorbidities = []
            if patient_features.get("has_diabetes", 0) == 1:
                comorbidities.append("Diabetes")
            if patient_features.get("has_hypertension", 0) == 1:
                comorbidities.append("Hypertension")
            if patient_features.get("has_heart_condition", 0) == 1:
                comorbidities.append("Heart Disease")
                
            if comorbidities:
                risk_factors.append({
                    "factor": "Comorbidities",
                    "value": ", ".join(comorbidities),
                    "impact": "high" if len(comorbidities) >= 2 else "medium"
                })
        
        return risk_factors
    
    # app/ml/mcp/service.py (add to existing implementation)

    def batch_predict(self, requests: List[ModelRequest]) -> List[ModelResponse]:
        """Make predictions for multiple requests using the MCP protocol."""
        start_time = time.time()
        
        # Group requests by model type for batch processing
        grouped_requests = {}
        for request in requests:
            model_id = request.model_id
            if model_id not in grouped_requests:
                grouped_requests[model_id] = []
            grouped_requests[model_id].append(request)
        
        # Process each group of requests
        responses = []
        for model_id, model_requests in grouped_requests.items():
            # Validate model exists
            if model_id not in self.model_registry:
                raise ValueError(f"Model {model_id} not found")
            
            model_metadata = self.model_registry[model_id]
            model_type = model_metadata.model_type
            
            # Route to appropriate batch prediction function based on model type
            if model_type == ModelType.READMISSION_RISK:
                batch_responses = self._batch_predict_readmission_risk(model_requests)
            elif model_type == ModelType.PATIENT_RISK:
                batch_responses = self._batch_predict_patient_risk(model_requests)
            else:
                # Fallback to individual processing if no batch function available
                batch_responses = [self.predict(request) for request in model_requests]
            
            responses.extend(batch_responses)
        
        # Log performance
        execution_time = time.time() - start_time
        logger.info(f"Batch prediction completed for {len(requests)} requests in {execution_time:.2f}s")
        
        return responses

    def _batch_predict_readmission_risk(self, requests: List[ModelRequest]) -> List[ModelResponse]:
        """Batch predict readmission risk for multiple patients."""
        # Extract patient IDs
        patient_ids = []
        request_map = {}  # Map patient_id to request
        
        for request in requests:
            patient_id = request.context.patient_id
            if not patient_id:
                if "patient_id" in request.inputs:
                    patient_id = request.inputs["patient_id"]
                else:
                    raise ValueError("Patient ID not provided in context or inputs")
            
            patient_ids.append(patient_id)
            request_map[patient_id] = request
        
        # Get features for all patients
        features_list = []
        valid_patient_ids = []
        
        for patient_id in patient_ids:
            features = self.feature_store.get_features_for_entity(
                "readmission_prediction", patient_id
            )
            
            if features:
                features_list.append(features)
                valid_patient_ids.append(patient_id)
        
        if not valid_patient_ids:
            raise ValueError("No valid patients found for batch prediction")
        
        # Get endpoint name based on first model ID (all should be the same)
        model_id = requests[0].model_id
        endpoint_name = self._get_endpoint_name(model_id)
        
        # Use SageMaker batch transform or create a batch of predictions
        sagemaker_responses = self.sagemaker.batch_predict(
            endpoint_name, features_list, valid_patient_ids
        )
        
        # Process responses
        responses = []
        for patient_id, prediction_result in zip(valid_patient_ids, sagemaker_responses):
            request = request_map[patient_id]
            
            # Extract risk score from response
            risk_score = prediction_result.get("score", 0.0)
            
            # Determine risk level based on score
            risk_level = "Low"
            if risk_score >= 0.7:
                risk_level = "High"
            elif risk_score >= 0.3:
                risk_level = "Medium"
            
            # Generate explanation if requested
            explanation = None
            if request.context.include_explanations:
                feature_importance = prediction_result.get("feature_importance", {})
                if not feature_importance:
                    # Get from individual feature store record
                    features = features_list[valid_patient_ids.index(patient_id)]
                    feature_importance = self._get_feature_importance(
                        request.model_id, 
                        features, 
                        prediction_result
                    )
                    
                explanation = ModelExplanation(
                    format=ExplanationFormat.FEATURE_IMPORTANCE,
                    explanation="Key factors contributing to readmission risk",
                    importance_scores=feature_importance
                )
            
            # Construct MCP response
            response = ModelResponse(
                model_id=request.model_id,
                version=self.model_registry[request.model_id].version,
                prediction={
                    "risk_score": risk_score,
                    "risk_percentage": round(risk_score * 100, 1),
                    "risk_level": risk_level,
                    "patient_id": patient_id,
                    "key_factors": self._get_key_risk_factors(
                        features_list[valid_patient_ids.index(patient_id)], 
                        feature_importance if explanation else None
                    )
                },
                confidence=prediction_result.get("confidence", 0.8),
                explanation=explanation,
                metadata={
                    "inference_time_ms": prediction_result.get("inference_time_ms", 0),
                    "model_type": ModelType.READMISSION_RISK.value,
                    "batch_processed": True
                }
            )
            
            responses.append(response)
        
        return responses