# app/ml/feature_store.py
import pandas as pd
import polars as pl
from typing import Dict, List, Any, Optional
import json
import hashlib
import os
from datetime import datetime
from app.config.settings import AppConfig
from app.utils.logging import get_logger
from app.ml.feature_engineering import FeatureEngineering

class FeatureStore:
    """Manages feature storage and retrieval for ML models."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.feature_engineering = FeatureEngineering()
        self.storage_dir = os.path.join(AppConfig.DATA_DIR, 'features')
        os.makedirs(self.storage_dir, exist_ok=True)
    
    def get_feature_set(self, feature_set_name: str, force_refresh: bool = False) -> pl.DataFrame:
        """
        Get a feature set, either from cache or by generating it.
        
        Args:
            feature_set_name: Name of the feature set
            force_refresh: Whether to force regeneration of features
            
        Returns:
            DataFrame containing the features
        """
        file_path = os.path.join(self.storage_dir, f"{feature_set_name}.parquet")
        metadata_path = os.path.join(self.storage_dir, f"{feature_set_name}_metadata.json")
        
        # Check if we have a recent cached version
        if not force_refresh and os.path.exists(file_path) and os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Check if cache is recent enough (less than 24 hours old)
            cache_time = datetime.fromisoformat(metadata['timestamp'])
            age_hours = (datetime.now() - cache_time).total_seconds() / 3600
            
            if age_hours < 24:  # Cache is fresh
                self.logger.info(f"Loading {feature_set_name} features from cache")
                return pl.read_parquet(file_path)
        
        # Generate new features
        self.logger.info(f"Generating fresh {feature_set_name} features")
        features_df = self.feature_engineering.extract_features(feature_set_name)
        
        # Save to cache
        features_df.write_parquet(file_path)
        
        # Save metadata
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'row_count': features_df.height,
            'column_count': features_df.width,
            'columns': features_df.columns
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
        
        return features_df
    
    def get_features_for_entity(self, feature_set_name: str, entity_id: str) -> Dict[str, Any]:
        """
        Get features for a specific entity (e.g., patient).
        
        Args:
            feature_set_name: Name of the feature set
            entity_id: ID of the entity (e.g., registry_id)
            
        Returns:
            Dictionary of feature values
        """
        features_df = self.get_feature_set(feature_set_name)
        
        # Find the entity in the DataFrame
        entity_filter = pl.col("registry_id") == entity_id
        entity_features = features_df.filter(entity_filter)
        
        if entity_features.height == 0:
            self.logger.warning(f"No features found for entity {entity_id} in {feature_set_name}")
            return {}
        
        # Convert to dictionary
        return entity_features.row(0, named=True)