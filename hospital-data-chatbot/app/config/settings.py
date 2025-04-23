# app/config/settings.py
import os
from typing import Dict, Any

class AppConfig:
    """Application configuration settings."""
    
    # Environment selection
    ENV = os.getenv('APP_ENV', 'dev_local')  # Options: dev_local, dev_cloud, stage, prod
    
    # Basic settings without defaults that would override env-specific configs
    DEBUG = os.getenv('DEBUG') == 'True' if os.getenv('DEBUG') else None
    PORT = os.getenv('PORT')
    DATA_DIR = os.getenv('DATA_DIR')
    
    # Environment-specific configurations
    _env_configs: Dict[str, Dict[str, Any]] = {
        'dev_local': {
            'DEBUG': True,
            'PORT': '8080',
            'DATA_DIR': 'data',
            'DB_HOST': 'localhost',
            'DB_PORT': 5432,
            'DB_NAME': 'hospital_data_test',
            'DB_USER': 'postgres',
            'DB_PASSWORD': 'postgres',
            'USE_S3': False,
            'AWS_REGION': 'us-east-1',
            'LOG_LEVEL': 'DEBUG',
            'API_KEY_REQUIRED': False,
        },
        'dev_cloud': {
            'DEBUG': True,
            'PORT': '8080',
            'DATA_DIR': 'data',
            'DB_HOST': 'dev-aurora-cluster.cluster-xyz.us-east-1.rds.amazonaws.com',
            'DB_PORT': 5432,
            'DB_NAME': 'hospital_data_dev',
            'DB_USER': 'dev_user',
            'DB_PASSWORD': os.getenv('DEV_DB_PASSWORD', 'dev_password'),
            'USE_S3': True,
            'S3_BUCKET': 'hospital-data-chatbot-dev',
            'AWS_REGION': 'us-east-1',
            'LOG_LEVEL': 'DEBUG',
            'API_KEY_REQUIRED': True,
        },
        'stage': {
            'DEBUG': False,
            'PORT': '8080',
            'DATA_DIR': 'data',
            'DB_HOST': 'stage-aurora-cluster.cluster-xyz.us-east-1.rds.amazonaws.com',
            'DB_PORT': 5432,
            'DB_NAME': 'hospital_data_stage',
            'DB_USER': 'stage_user',
            'DB_PASSWORD': os.getenv('STAGE_DB_PASSWORD', 'stage_password'),
            'USE_S3': True,
            'S3_BUCKET': 'hospital-data-chatbot-stage',
            'AWS_REGION': 'us-east-1',
            'LOG_LEVEL': 'INFO',
            'API_KEY_REQUIRED': True,
        },
        'prod': {
            'DEBUG': False,
            'PORT': '8080',
            'DATA_DIR': 'data',
            'DB_HOST': 'prod-aurora-cluster.cluster-xyz.us-east-1.rds.amazonaws.com',
            'DB_PORT': 5432,
            'DB_NAME': 'hospital_data_prod',
            'DB_USER': 'prod_user',
            'DB_PASSWORD': os.getenv('PROD_DB_PASSWORD', 'change_this_in_prod'),
            'USE_S3': True,
            'S3_BUCKET': 'hospital-data-chatbot-prod',
            'AWS_REGION': 'us-east-1',
            'LOG_LEVEL': 'WARNING',
            'API_KEY_REQUIRED': True,
        }
    }
    
    # Apply environment-specific settings - first set defaults
    env_config = _env_configs.get(ENV, _env_configs['dev_local'])
    
    # Now apply the environment config
    for key, value in env_config.items():
        locals()[key] = value
    
    # Override with environment variables if they exist
    for key in env_config.keys():
        env_value = os.getenv(key)
        if env_value is not None:
            # Handle special cases for type conversion
            if key == 'DEBUG' or key == 'USE_S3' or key == 'API_KEY_REQUIRED':
                locals()[key] = env_value.lower() == 'true'
            elif key == 'DB_PORT':
                locals()[key] = int(env_value)
            else:
                locals()[key] = env_value
    
    # Bedrock settings
    BEDROCK_MODEL_ID = os.getenv(
        'BEDROCK_MODEL_ID', 
        'anthropic.claude-3-sonnet-20240229-v1:0'
    )
    
    # Security settings - ensure API_KEY is always from env var if provided
    API_KEY = os.getenv('API_KEY', 'default_dev_key')  # Change in production!
    
    @classmethod
    def get_environment_name(cls) -> str:
        """Get a human-readable name for the current environment."""
        env_names = {
            'dev_local': 'Development (Local)',
            'dev_cloud': 'Development (Cloud)',
            'stage': 'Staging',
            'prod': 'Production'
        }
        return env_names.get(cls.ENV, cls.ENV)
    
    @classmethod
    def is_development(cls) -> bool:
        """Check if the current environment is a development environment."""
        return cls.ENV.startswith('dev')
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if the current environment is production."""
        return cls.ENV == 'prod'