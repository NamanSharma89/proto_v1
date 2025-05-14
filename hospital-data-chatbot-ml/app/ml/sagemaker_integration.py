# app/ml/sagemaker_integration.py
import boto3
import json
import os
import numpy as np
import polars as pl
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import time
import io
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
    
# Enhanced SageMaker integration with better error handling

    def train_model(self, model_name, feature_set_name, target_column, instance_type="ml.m5.large", hyperparameters=None):
        """
        Train a new model using SageMaker with enhanced error handling.
        
        Args:
            model_name: Name of the model
            feature_set_name: Name of the feature set
            target_column: Target column for prediction
            instance_type: SageMaker instance type
            hyperparameters: Model hyperparameters
            
        Returns:
            Dictionary with training job information
        """
        try:
            # Get features
            features_df = self.feature_store.get_feature_set(feature_set_name)
            
            # Split train/test
            train_df, test_df = self._split_train_test(features_df)
            
            # Upload to S3
            s3_bucket = AppConfig.S3_BUCKET
            s3_prefix = f"sagemaker/{model_name}"
            training_data_key = f"{s3_prefix}/train/train.csv"
            test_data_key = f"{s3_prefix}/test/test.csv"
            
            # Upload data to S3
            upload_to_s3(train_df, s3_bucket, training_data_key)
            upload_to_s3(test_df, s3_bucket, test_data_key)
            
            # Create SageMaker training job
            training_job_name = f"{model_name}-{int(time.time())}"
            
            # Use XGBoost as default algorithm
            image_uri = f"683313688378.dkr.ecr.{AppConfig.AWS_REGION}.amazonaws.com/sagemaker-xgboost:1.5-1"
            
            # Set hyperparameters
            if not hyperparameters:
                # Determine if binary or multiclass classification
                unique_values = pl.Series(train_df[target_column]).unique()
                num_classes = len(unique_values)
                
                hyperparameters = {
                    'objective': 'binary:logistic' if num_classes <= 2 else 'multi:softmax',
                    'num_round': '100',
                    'max_depth': '6',
                    'eta': '0.3',
                    'eval_metric': 'auc' if num_classes <= 2 else 'merror',
                    'num_class': str(num_classes) if num_classes > 2 else None
                }
                # Remove None values
                hyperparameters = {k: v for k, v in hyperparameters.items() if v is not None}
            
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
                    'S3OutputPath': f"s3://{s3_bucket}/{s3_prefix}/output"
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
                'algorithm': 'xgboost',
                'hyperparameters': hyperparameters,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error training model: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to train model: {str(e)}")
    
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
        feature_df = pl.DataFrame([features])
        
        # Convert to CSV without headers
        csv_buffer = io.StringIO()
        feature_df.write_csv(csv_buffer, include_header=False)
        csv_data = csv_buffer.getvalue()
        
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
        n_rows = df.height
        random_values = np.random.random(n_rows)
        df = df.with_column(pl.Series("_split_col", random_values))
        
        # Split based on random value
        train_df = df.filter(pl.col('_split_col') >= test_size)
        test_df = df.filter(pl.col('_split_col') < test_size)
        
        # Remove the split column
        train_df = train_df.drop('_split_col')
        test_df = test_df.drop('_split_col')
        
        return train_df, test_df
    # app/ml/sagemaker_integration.py (add to existing implementation)

    def batch_predict(self, endpoint_name: str, features_list: List[Dict[str, Any]], 
                    reference_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get predictions for multiple inputs from a deployed model.
        
        Args:
            endpoint_name: Name of the SageMaker endpoint
            features_list: List of feature dictionaries
            reference_ids: Optional list of reference IDs (e.g., patient IDs)
            
        Returns:
            List of prediction results
        """
        try:
            # For small batches (< 20), use direct invocation
            if len(features_list) < 20:
                # Convert features to CSV
                csv_buffer = io.StringIO()
                feature_df = pl.DataFrame(features_list)
                feature_df.write_csv(csv_buffer, include_header=True)
                csv_data = csv_buffer.getvalue()
                
                # Get prediction from endpoint
                response = self.sagemaker_runtime.invoke_endpoint(
                    EndpointName=endpoint_name,
                    ContentType='text/csv',
                    Body=csv_data,
                    Accept='application/json'
                )
                
                # Parse and process response
                result = json.loads(response['Body'].read().decode())
                
                # If result is not a list, convert to list of same result
                if not isinstance(result, list):
                    result = [result] * len(features_list)
                    
                # Add reference IDs if provided
                if reference_ids:
                    for i, r in enumerate(result):
                        if i < len(reference_ids):
                            r['reference_id'] = reference_ids[i]
                
                return result
                
            # For larger batches, use Batch Transform
            else:
                # Create a unique job name
                batch_job_name = f"{endpoint_name}-batch-{int(time.time())}"
                
                # Save features to S3
                s3_input_path = self._save_features_to_s3(features_list, reference_ids)
                
                # Create output path
                s3_output_path = f"s3://{AppConfig.S3_BUCKET}/batch-predictions/{batch_job_name}"
                
                # Start batch transform job
                response = self.sagemaker_client.create_transform_job(
                    TransformJobName=batch_job_name,
                    ModelName=self._get_model_name_from_endpoint(endpoint_name),
                    TransformInput={
                        'DataSource': {
                            'S3DataSource': {
                                'S3DataType': 'S3Prefix',
                                'S3Uri': s3_input_path
                            }
                        },
                        'ContentType': 'text/csv',
                        'SplitType': 'Line'
                    },
                    TransformOutput={
                        'S3OutputPath': s3_output_path,
                        'Accept': 'application/json',
                        'AssembleWith': 'Line'
                    },
                    TransformResources={
                        'InstanceType': 'ml.m5.large',
                        'InstanceCount': 1
                    }
                )
                
                # Wait for batch transform job to complete
                self.sagemaker_client.get_waiter('transform_job_completed_or_stopped').wait(
                    TransformJobName=batch_job_name
                )
                
                # Get results from S3
                results = self._get_batch_results_from_s3(s3_output_path)
                
                return results
                
        except Exception as e:
            self.logger.error(f"Error in batch prediction: {str(e)}", exc_info=True)
            raise
            
    def _save_features_to_s3(self, features_list: List[Dict[str, Any]], 
                            reference_ids: List[str] = None) -> str:
        """Save features to S3 for batch processing."""
        # Convert to DataFrame
        df = pl.DataFrame(features_list)
        
        # Add reference IDs if provided
        if reference_ids:
            df = df.with_column(pl.Series("reference_id", reference_ids))
        
        # Save to CSV in memory
        csv_buffer = io.BytesIO()
        df.write_csv(csv_buffer, include_header=True)
        csv_buffer.seek(0)
        
        # Upload to S3
        bucket = AppConfig.S3_BUCKET
        timestamp = int(time.time())
        key = f"batch-input/features-{timestamp}.csv"
        
        s3_client = boto3.client('s3')
        s3_client.upload_fileobj(
            csv_buffer,
            bucket,
            key,
            ExtraArgs={'ContentType': 'text/csv'}
        )
        
        return f"s3://{bucket}/{key}"
        
    def _get_batch_results_from_s3(self, s3_output_path: str) -> List[Dict[str, Any]]:
        """Get batch prediction results from S3."""
        # Parse S3 URI
        bucket, prefix = self._parse_s3_uri(s3_output_path)
        
        # List objects in the output path
        s3_client = boto3.client('s3')
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )
        
        # Get the output file
        results = []
        for obj in response.get('Contents', []):
            # Skip any non-data files
            if obj['Key'].endswith('/'):
                continue
                
            # Download the file
            output = io.BytesIO()
            s3_client.download_fileobj(bucket, obj['Key'], output)
            output.seek(0)
            
            # Parse the results
            for line in output.readlines():
                try:
                    result = json.loads(line.decode('utf-8'))
                    results.append(result)
                except json.JSONDecodeError:
                    self.logger.warning(f"Could not parse line as JSON: {line}")
        
        return results
        
    def _parse_s3_uri(self, uri: str) -> Tuple[str, str]:
        """Parse S3 URI into bucket and prefix."""
        # Remove 's3://' prefix
        path = uri.replace('s3://', '')
        
        # Split into bucket and prefix
        parts = path.split('/', 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ''
        
        return bucket, prefix
        
    def _get_model_name_from_endpoint(self, endpoint_name: str) -> str:
        """Get the model name associated with an endpoint."""
        # Describe the endpoint
        response = self.sagemaker_client.describe_endpoint(
            EndpointName=endpoint_name
        )
        
        # Get the endpoint config name
        endpoint_config_name = response['EndpointConfigName']
        
        # Describe the endpoint config
        config_response = self.sagemaker_client.describe_endpoint_config(
            EndpointConfigName=endpoint_config_name
        )
        
        # Get the model name from the first production variant
        model_name = config_response['ProductionVariants'][0]['ModelName']
        
        return model_name