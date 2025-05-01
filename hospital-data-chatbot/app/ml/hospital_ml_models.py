# app/ml/hospital_ml_models.py
from typing import Dict, List, Any, Optional
import polars as pl
import numpy as np
import json
import os
from datetime import datetime
from app.config.settings import AppConfig
from app.utils.logging import get_logger
from app.ml.feature_store import FeatureStore
from app.ml.sagemaker_integration import SageMakerIntegration

class HospitalMLModels:
    """
    Manages machine learning models for hospital data analysis.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.feature_store = FeatureStore()
        self.sagemaker = SageMakerIntegration()
        self.models_dir = os.path.join(AppConfig.DATA_DIR, 'models')
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Load model registry
        self.registry_path = os.path.join(self.models_dir, 'model_registry.json')
        self.model_registry = self._load_model_registry()
    
    def get_readmission_risk(self, patient_id: str) -> Dict[str, Any]:
        """
        Predict the risk of 30-day readmission for a patient.
        
        Args:
            patient_id: The patient's registry ID
            
        Returns:
            Dictionary with readmission risk prediction and details
        """
        # Get the endpoint name from registry
        endpoint_name = self._get_latest_endpoint('readmission_prediction')
        
        if not endpoint_name:
            self.logger.warning("No readmission prediction model endpoint found")
            return {
                'status': 'error',
                'message': 'No deployed model available',
                'risk_score': None
            }
        
        # Get patient features
        patient_features = self.feature_store.get_features_for_entity(
            'readmission_prediction', patient_id
        )
        
        if not patient_features:
            self.logger.warning(f"No features found for patient {patient_id}")
            return {
                'status': 'error',
                'message': f'No data available for patient {patient_id}',
                'risk_score': None
            }
        
        # Remove target column if present
        if 'readmitted_30_days' in patient_features:
            del patient_features['readmitted_30_days']
        
        # Get prediction
        try:
            prediction = self.sagemaker.get_prediction(endpoint_name, patient_features)
            
            # Extract readmission risk score (format depends on the model)
            if isinstance(prediction['prediction'], dict) and 'score' in prediction['prediction']:
                risk_score = prediction['prediction']['score']
            elif isinstance(prediction['prediction'], list):
                risk_score = prediction['prediction'][0]
            else:
                risk_score = prediction['prediction']
            
            # Convert to percentage if between 0-1
            if isinstance(risk_score, (int, float)) and 0 <= risk_score <= 1:
                risk_percentage = risk_score * 100
            else:
                risk_percentage = risk_score
            
            risk_level = 'Low'
            if risk_percentage >= 70:
                risk_level = 'High'
            elif risk_percentage >= 30:
                risk_level = 'Medium'
            
            return {
                'status': 'success',
                'patient_id': patient_id,
                'risk_score': risk_score,
                'risk_percentage': round(risk_percentage, 1),
                'risk_level': risk_level,
                'key_factors': self._get_key_risk_factors(patient_features),
                'model_info': {
                    'endpoint': endpoint_name,
                    'timestamp': datetime.now().isoformat()
                }
            }
        
        except Exception as e:
            self.logger.error(f"Error getting readmission prediction: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Prediction error: {str(e)}',
                'risk_score': None
            }
    
# app/ml/hospital_ml_models.py (continued)

    def get_patient_risk_stratification(self, patient_id: str = None) -> Dict[str, Any]:
        """
        Get risk stratification for a specific patient or all patients.
        
        Args:
            patient_id: Optional patient registry ID. If None, returns stratification for all patients.
            
        Returns:
            Dictionary with risk stratification results
        """
        # Get features from feature store
        features_df = self.feature_store.get_feature_set('patient_risk_factors')
        
        # If patient_id provided, filter for just that patient
        if patient_id:
            features_df = features_df.filter(pl.col('registry_id') == patient_id)
            
            if features_df.height == 0:
                return {
                    'status': 'error',
                    'message': f'No data found for patient {patient_id}'
                }
        
        # Define risk tiers based on features
        features_df = features_df.with_columns([
            # Compute a simple risk score based on age, comorbidities, and stay duration
            (
                # Age factor: 0-1 scale based on age group
                pl.when(pl.col("age") < 40).then(0.2)
                  .when((pl.col("age") >= 40) & (pl.col("age") < 60)).then(0.5)
                  .when((pl.col("age") >= 60) & (pl.col("age") < 80)).then(0.8)
                  .otherwise(1.0) * 0.4  # 40% weight
                
                # Comorbidity factor
                + pl.col("comorbidity_score").clip(0, 5) / 5 * 0.4  # 40% weight
                
                # Stay duration factor (compared to average)
                + pl.when(pl.col("relative_stay_duration") < 0.5).then(0.1)
                  .when((pl.col("relative_stay_duration") >= 0.5) & (pl.col("relative_stay_duration") < 1.0)).then(0.3)
                  .when((pl.col("relative_stay_duration") >= 1.0) & (pl.col("relative_stay_duration") < 1.5)).then(0.6)
                  .otherwise(0.9) * 0.2  # 20% weight
            ).alias("risk_score"),
            
            # Risk level classification
            pl.when(
                (pl.col("age") >= 70) & 
                (pl.col("comorbidity_score") >= 3) & 
                (pl.col("diagnosis_count") >= 5)
            ).then("very_high")
            .when(
                (pl.col("age") >= 60) & 
                (pl.col("comorbidity_score") >= 2)
            ).then("high")
            .when(
                (pl.col("age") >= 50) & 
                (pl.col("comorbidity_score") >= 1)
            ).then("moderate")
            .otherwise("low").alias("risk_level")
        ])
        
        # Calculate risk distribution
        risk_distribution = (
            features_df.group_by("risk_level")
            .agg(pl.count().alias("patient_count"))
            .sort("risk_level")
        )
        
        # Calculate overall stats
        total_patients = features_df.height
        avg_risk_score = features_df["risk_score"].mean()
        
        # Prepare result structure
        if patient_id:
            # Single patient result
            patient_data = features_df.row(0, named=True)
            
            return {
                'status': 'success',
                'patient_id': patient_id,
                'risk_score': round(float(patient_data['risk_score']), 2),
                'risk_level': patient_data['risk_level'],
                'risk_factors': {
                    'age': int(patient_data['age']),
                    'comorbidity_score': int(patient_data['comorbidity_score']),
                    'diagnosis_count': int(patient_data['diagnosis_count']),
                    'relative_stay_duration': round(float(patient_data['relative_stay_duration']), 2)
                }
            }
        else:
            # Population-level results
            return {
                'status': 'success',
                'total_patients': total_patients,
                'average_risk_score': round(float(avg_risk_score), 2),
                'risk_distribution': risk_distribution.to_dicts(),
                'high_risk_count': features_df.filter(
                    pl.col('risk_level').is_in(['high', 'very_high'])
                ).height,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_diagnosis_clusters(self, min_cluster_size: int = 5) -> Dict[str, Any]:
        """
        Get clusters of similar diagnoses based on pattern analysis.
        
        Args:
            min_cluster_size: Minimum number of diagnoses in a cluster
            
        Returns:
            Dictionary with diagnosis clustering results
        """
        try:
            # Get features for clustering
            features_df = self.feature_store.get_feature_set('diagnosis_clustering')
            
            # Basic implementation: create diagnosis groups based on key terms
            # In a real implementation, you would use a proper clustering algorithm here
            # with ML models trained on diagnosis text similarity
            
            # Define some common diagnosis patterns for grouping
            diagnosis_patterns = {
                'cardiovascular': ['heart', 'cardio', 'hypertension', 'angina', 'artery', 'stroke'],
                'respiratory': ['lung', 'pneumonia', 'copd', 'asthma', 'bronchitis', 'respiratory'],
                'gastrointestinal': ['stomach', 'intestinal', 'bowel', 'liver', 'pancreas', 'appendicitis'],
                'neurological': ['brain', 'neuro', 'seizure', 'epilepsy', 'alzheimer', 'parkinsons'],
                'endocrine': ['diabetes', 'thyroid', 'hormone', 'insulin', 'endocrine'],
                'infectious': ['infection', 'viral', 'bacterial', 'sepsis', 'influenza', 'covid'],
            }
            
            # Assign diagnoses to clusters
            diagnosis_groups = {}
            for diagnosis_row in features_df.to_dicts():
                diagnosis = diagnosis_row.get('diagnosis_cleaned', '').lower()
                
                # Find matching pattern
                assigned_group = 'other'
                for group, patterns in diagnosis_patterns.items():
                    if any(pattern in diagnosis for pattern in patterns):
                        assigned_group = group
                        break
                
                # Add to group
                if assigned_group not in diagnosis_groups:
                    diagnosis_groups[assigned_group] = []
                
                diagnosis_groups[assigned_group].append({
                    'diagnosis': diagnosis_row.get('diagnosis'),
                    'patient_count': diagnosis_row.get('patient_count'),
                    'avg_age': round(diagnosis_row.get('avg_patient_age'), 1),
                    'avg_stay': round(diagnosis_row.get('avg_stay_duration'), 1),
                    'male_ratio': round(diagnosis_row.get('male_ratio', 0.5), 2)
                })
            
            # Calculate stats for each group
            group_stats = {}
            for group, diagnoses in diagnosis_groups.items():
                if len(diagnoses) < min_cluster_size and group != 'other':
                    # Add to 'other' if below minimum size
                    if 'other' not in diagnosis_groups:
                        diagnosis_groups['other'] = []
                    diagnosis_groups['other'].extend(diagnoses)
                    continue
                
                # Calculate group stats
                total_patients = sum(d.get('patient_count', 0) for d in diagnoses)
                avg_age = sum(d.get('avg_age', 0) * d.get('patient_count', 0) for d in diagnoses) / total_patients if total_patients > 0 else 0
                avg_stay = sum(d.get('avg_stay', 0) * d.get('patient_count', 0) for d in diagnoses) / total_patients if total_patients > 0 else 0
                
                group_stats[group] = {
                    'diagnosis_count': len(diagnoses),
                    'total_patients': total_patients,
                    'avg_age': round(avg_age, 1),
                    'avg_stay': round(avg_stay, 1),
                    'top_diagnoses': sorted(diagnoses, key=lambda d: d.get('patient_count', 0), reverse=True)[:5]
                }
            
            # Remove empty groups and those below threshold
            group_stats = {k: v for k, v in group_stats.items() if v['diagnosis_count'] >= min_cluster_size or k == 'other'}
            
            return {
                'status': 'success',
                'cluster_count': len(group_stats),
                'clusters': group_stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting diagnosis clusters: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Error generating diagnosis clusters: {str(e)}'
            }
    
    def _get_key_risk_factors(self, patient_features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract key risk factors from patient features."""
        risk_factors = []
        
        # Age as risk factor
        if 'age' in patient_features:
            age = patient_features['age']
            if age >= 65:
                risk_factors.append({
                    'factor': 'Advanced Age',
                    'value': f"{age} years",
                    'impact': 'high' if age >= 75 else 'medium'
                })
        
        # Comorbidities
        comorbidities = []
        if patient_features.get('has_diabetes', 0) == 1:
            comorbidities.append('Diabetes')
        if patient_features.get('has_hypertension', 0) == 1:
            comorbidities.append('Hypertension')
        if patient_features.get('has_heart_condition', 0) == 1:
            comorbidities.append('Heart Disease')
        if patient_features.get('has_kidney_condition', 0) == 1:
            comorbidities.append('Kidney Disease')
        if patient_features.get('has_liver_condition', 0) == 1:
            comorbidities.append('Liver Disease')
        
        if comorbidities:
            risk_factors.append({
                'factor': 'Comorbidities',
                'value': ', '.join(comorbidities),
                'impact': 'high' if len(comorbidities) >= 2 else 'medium'
            })
        
        # Multiple diagnoses
        diagnosis_count = patient_features.get('diagnosis_count', 0)
        if diagnosis_count >= 3:
            risk_factors.append({
                'factor': 'Multiple Diagnoses',
                'value': f"{diagnosis_count} diagnoses",
                'impact': 'high' if diagnosis_count >= 5 else 'medium'
            })
        
        # Long stay duration
        stay_duration = patient_features.get('stay_duration', 0)
        if stay_duration >= 7:
            risk_factors.append({
                'factor': 'Extended Hospital Stay',
                'value': f"{stay_duration} days",
                'impact': 'high' if stay_duration >= 14 else 'medium'
            })
        
        return risk_factors
    
    def _load_model_registry(self) -> Dict[str, Any]:
        """Load the model registry from disk or create a new one."""
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading model registry: {str(e)}", exc_info=True)
        
        # Create a new registry if it doesn't exist or couldn't be loaded
        registry = {
            'models': {},
            'endpoints': {},
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        with open(self.registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
            
        return registry
    
    def _get_latest_endpoint(self, model_type: str) -> Optional[str]:
        """Get the most recent endpoint for a given model type."""
        if 'endpoints' not in self.model_registry:
            return None
        
        # Find endpoints for this model type
        matching_endpoints = []
        for endpoint_name, endpoint_info in self.model_registry['endpoints'].items():
            if endpoint_info.get('model_type') == model_type and endpoint_info.get('status') == 'InService':
                matching_endpoints.append((endpoint_name, endpoint_info))
        
        if not matching_endpoints:
            return None
        
        # Sort by creation timestamp and get the most recent
        matching_endpoints.sort(key=lambda x: x[1].get('created_at', ''), reverse=True)
        return matching_endpoints[0][0]