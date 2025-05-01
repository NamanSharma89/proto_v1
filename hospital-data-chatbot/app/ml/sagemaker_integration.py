# app/ml/sagemaker_integration.py
import boto3
import json
import os
import numpy as np
import pandas as pd
import polars as pl
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import time
from app.config.settings import AppConfig
from app.utils.logging import get_logger
from app.ml.feature_store import FeatureStore

class SageMakerIntegration:
    """Handles integration with AWS SageMaker for ML model training and inference."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.sagemaker_client = boto3.client('sagemaker', region_name=AppConfig.AWS_REGION)
        self.sagemaker_runtime = boto3.client('sagemaker-runtime', region_name=AppConfig.AWS_REGION)
        self.feature_store = FeatureStore()
    
    def train_model(self, model_name: str, feature_set_name: str, 
                    target_column: str, instance_type: str = 'ml.m5.large',
                    hyperparameters: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Train a new model using SageMaker.
        
        Args:
            model_name: Name of the model to train
            feature_set_name: Name of the feature set to use
            target_column: Name of the target column for prediction
            instance_type: SageMaker instance type to use
            hyperparameters: Optional hyperparameters for the model
            
        Returns:
            Dictionary with training job information
        """
        # Get features
        features_df = self.feature_store.get_feature_set(feature_set_name)
        
        # Split into train/test
        train_df, test_df = self._split_train_test(features_df)
        
        # Ensure S3 directories exist
        s3_bucket = AppConfig.S3_BUCKET
        s3_prefix = f"sagemaker/{model_name}"
        training_data_key = f"{s3_prefix}/train/train.csv"
        test_data_key = f"{s3_prefix}/test/test.csv"
        output_key = f"{s3_prefix}/output"
        
        # Upload data to S3
        s3 = boto3.resource('s3')
        
        # Convert Polars to pandas for S3 upload
        train_pandas = train_df.to_pandas()
        test_pandas = test_df.to_pandas()
        
        # Save train set
        train_csv_buffer = train_pandas.to_csv(index=False).encode('utf-8')
        s3.Object(s3_bucket, training_data_key).put(Body=train_csv_buffer)
        
        # Save test set
        test_csv_buffer = test_pandas.to_csv(index=False).encode('utf-8')
        s3.Object(s3_bucket, test_data_key).put(Body=test_csv_buffer)
        
        # Set up SageMaker training job
        training_job_name = f"{model_name}-{int(time.time())}"
        
        # Set algorithm based on model name
        if 'xgboost' in model_name.lower():
            algorithm_name = 'xgboost'
            image_uri = f"683313688378.dkr.ecr.{AppConfig.AWS_REGION}.amazonaws.com/sagemaker-xgboost:1.5-1"
        elif 'linear' in model_name.lower():
            algorithm_name = 'linear-learner'
            image_uri = f"683313688378.dkr.ecr.{AppConfig.AWS_REGION}.amazonaws.com/linear-learner:1"
        else:
            algorithm_name = 'xgboost'  # Default to XGBoost
            image_uri = f"683313688378.dkr.ecr.{AppConfig.AWS_REGION}.amazonaws.com/sagemaker-xgboost:1.5-1"
        
        # Set hyperparameters
        if not hyperparameters:
            if algorithm_name == 'xgboost':
                hyperparameters = {
                    'objective': 'binary:logistic' if len(train_df[target_column].unique()) <= 2 else 'multi:softmax',
                    'num_round': '100',
                    'max_depth': '6',
                    'eta': '0.3',
                    'eval_metric': 'auc' if len(train_df[target_column].unique()) <= 2 else 'merror'
                }
            else:
                hyperparameters = {
                    'predictor_type': 'binary_classifier' if len(train_df[target_column].unique()) <= 2 else 'multiclass_classifier',
                    'num_classes': str(len(train_df[target_column].unique())),
                    'mini_batch_size': '100'
                }
        
        # Create training job
        response = self.sagemaker_client.create_training_job(
            TrainingJobName=training_job_name,
            AlgorithmSpecification={
                'TrainingImage': image_uri,
                'TrainingInputMode': 'File'
            },
            RoleArn=AppConfig.SAGEMAKER_ROLE_ARN,
            InputDataConfig=[
                {
                    'ChannelName': 'train',
                    'DataSource': {
                        'S3DataSource': {
                            'S3DataType': 'S3Prefix',
                            'S3Uri': f"s3://{s3_bucket}/{s3_prefix}/train",
                            'S3DataDistributionType': 'FullyReplicated'
                        }
                    },
                    'ContentType': 'text/csv'
                },
                {
                    'ChannelName': 'validation',
                    'DataSource': {
                        'S3DataSource': {
                            'S3DataType': 'S3Prefix',
                            'S3Uri': f"s3://{s3_bucket}/{s3_prefix}/test",
                            'S3DataDistributionType': 'FullyReplicated'
                        }
                    },
                    'ContentType': 'text/csv'
                }
            ],
            OutputDataConfig={
                'S3OutputPath': f"s3://{s3_bucket}/{output_key}"
            },
            ResourceConfig={
                'InstanceType': instance_type,
                'InstanceCount': 1,
                'VolumeSizeInGB': 30
            },
            StoppingCondition={
                'MaxRuntimeInSeconds': 86400  # 24 hours
            },
            HyperParameters=hyperparameters
        )
        
        self.logger.info(f"Started training job: {training_job_name}")
        
        return {
            'job_name': training_job_name,
            'model_name': model_name,
            'feature_set': feature_set_name,
            'target_column': target_column,
            'algorithm': algorithm_name,
            'hyperparameters': hyperparameters,
            'timestamp': datetime.now().isoformat()
        }
    
    def deploy_model(self, training_job_name: str, instance_type: str = 'ml.t2.medium') -> Dict[str, Any]:
        """
        Deploy a trained model to a SageMaker endpoint.
        
        Args:
            training_job_name: Name of the completed training job
            instance_type: Instance type for the endpoint
            
        Returns:
            Dictionary with endpoint information
        """
        # Wait for training job to complete
        self.sagemaker_client.get_waiter('training_job_completed_or_stopped').wait(
            TrainingJobName=training_job_name
        )
        
        # Get training job info
        training_job = self.sagemaker_client.describe_training_job(
            TrainingJobName=training_job_name
        )
        
        # Create model
        model_name = f"{training_job_name}-model"
        model_data_url = training_job['ModelArtifacts']['S3ModelArtifacts']
        primary_container = {
            'Image': training_job['AlgorithmSpecification']['TrainingImage'],
            'ModelDataUrl': model_data_url
        }
        
        self.sagemaker_client.create_model(
            ModelName=model_name,
            PrimaryContainer=primary_container,
            ExecutionRoleArn=AppConfig.SAGEMAKER_ROLE_ARN
        )
        
        # Create endpoint configuration
        endpoint_config_name = f"{model_name}-config"
        self.sagemaker_client.create_endpoint_config(
            EndpointConfigName=endpoint_config_name,
            ProductionVariants=[
                {
                    'VariantName': 'AllTraffic',
                    'ModelName': model_name,
                    'InstanceType': instance_type,
                    'InitialInstanceCount': 1
                }
            ]
        )
        
        # Create endpoint
        endpoint_name = f"{model_name}-endpoint"
        self.sagemaker_client.create_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=endpoint_config_name
        )
        
        self.logger.info(f"Endpoint {endpoint_name} deployment initiated")
        
        return {
            'endpoint_name': endpoint_name,
            'model_name': model_name,
            'training_job': training_job_name,
            'instance_type': instance_type,
            'status': 'Creating',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_prediction(self, endpoint_name: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a prediction from a deployed model.
        
        Args:
            endpoint_name: Name of the SageMaker endpoint
            features: Dictionary of feature values
            
        Returns:
            Dictionary with prediction results
        """
        # Convert features to CSV
        feature_df = pd.DataFrame([features])
        csv_data = feature_df.to_csv(index=False, header=False)
        
        # Get prediction from endpoint
        response = self.sagemaker_runtime.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType='text/csv',
            Body=csv_data
        )
        
        # Parse response
        result = json.loads(response['Body'].read().decode())
        
        return {
            'prediction': result,
            'features': features,
            'endpoint': endpoint_name,
            'timestamp': datetime.now().isoformat()
        }
    
    def _split_train_test(self, df: pl.DataFrame, test_size: float = 0.2) -> Tuple[pl.DataFrame, pl.DataFrame]:
        """Split a DataFrame into training and test sets."""
        # Create a random column for splitting
        df = df.with_column(pl.lit(np.random.random(df.height)).alias('_split_col'))
        
        # Split based on random value
        train_df = df.filter(pl.col('_split_col') >= test_size)
        test_df = df.filter(pl.col('_split_col') < test_size)
        
        # Remove the split column
        train_df = train_df.drop('_split_col')
        test_df = test_df.drop('_split_col')
        
        return train_df, test_df