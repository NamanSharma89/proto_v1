# app/config/settings.py
import os
from typing import Dict, Any

class AppConfig:
    """Application configuration settings."""
    
    # Environment selection
    ENV = os.getenv('APP_ENV', 'dev_local')  # Options: dev_local, dev_cloud, stage, prod
    
    # Base configurations
    DEBUG = os.getenv('DEBUG', 'True') == 'True'
    PORT = os.getenv('PORT', '8080')
    
    # Data settings
    DATA_DIR = os.getenv('DATA_DIR', 'data')
    
    # Environment-specific configurations
    _env_configs: Dict[str, Dict[str, Any]] = {
        'dev_local': {
            'DEBUG': True,
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
            'DB_HOST': 'stage-aurora-cluster.cluster-xyz.us-east-1.rds.amazonaws.com',
            'DB_PORT': 5432,
            'DB_NAME': 'hospital_data_stage',
            'DB_USER': 'stage_user',
            'DB_PASSWORD': os.getenv('STAGE_DB_PASSWORD', None),
            'USE_S3': True,
            'S3_BUCKET': 'hospital-data-chatbot-stage',
            'AWS_REGION': 'us-east-1',
            'LOG_LEVEL': 'INFO',
            'API_KEY_REQUIRED': True,
        },
        'prod': {
            'DEBUG': False,
            'DB_HOST': 'prod-aurora-cluster.cluster-xyz.us-east-1.rds.amazonaws.com',
            'DB_PORT': 5432,
            'DB_NAME': 'hospital_data_prod',
            'DB_USER': 'prod_user',
            'DB_PASSWORD': os.getenv('PROD_DB_PASSWORD', None),
            'USE_S3': True,
            'S3_BUCKET': 'hospital-data-chatbot-prod',
            'AWS_REGION': 'us-east-1',
            'LOG_LEVEL': 'WARNING',
            'API_KEY_REQUIRED': True,
        }
    }
    
    # Apply environment-specific settings
    env_config = _env_configs.get(ENV, _env_configs['dev_local'])
    
    # Override base settings with environment-specific ones
    for key, value in env_config.items():
        # Only set if not explicitly defined in environment variables
        if key != 'ENV' and not os.getenv(key):
            locals()[key] = value
    
    # AWS settings (may be overridden by env-specific settings)
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    USE_S3 = os.getenv('USE_S3', 'False') == 'True'
    S3_BUCKET = os.getenv('S3_BUCKET', 'hospital-data-chatbot')
    
    # Database settings (may be overridden by env-specific settings)
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'hospital_data')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
    
    # Logging level
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Bedrock settings
    BEDROCK_MODEL_ID = os.getenv(
        'BEDROCK_MODEL_ID', 
        'anthropic.claude-3-sonnet-20240229-v1:0'
    )
    
    # Security settings
    API_KEY_REQUIRED = os.getenv('API_KEY_REQUIRED', 'True') == 'True'
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