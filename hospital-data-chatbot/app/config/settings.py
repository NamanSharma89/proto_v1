# app/config/settings.py
import os
from typing import Dict, Any
# Add to app/config/settings.py
import boto3

class AppConfig:
    """Application configuration settings."""
    
    # Environment selection
    ENV = os.getenv('APP_ENV', 'dev_local')  # Options: dev_local, dev-cloud, stage, prod
    
    # Basic settings without defaults that would override env-specific configs
    DEBUG = os.getenv('DEBUG') == 'True' if os.getenv('DEBUG') else None
    PORT = os.getenv('PORT')
    DATA_DIR = os.getenv('DATA_DIR')

    # app/config/settings.py (additions)

    # Ollama settings
    USE_OLLAMA = os.getenv('USE_OLLAMA', 'True').lower() == 'true'
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5-coder:14b')
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')    

    @classmethod
    def get_ssm_parameter(cls, parameter_name, default=None):
        """Fetch a parameter from AWS Systems Manager Parameter Store."""
        try:
            if cls.is_development() and not cls.USE_S3:
                # In local development without AWS, return default
                return default
                
            ssm = boto3.client('ssm', region_name=cls.AWS_REGION)
            response = ssm.get_parameter(
                Name=parameter_name,
                WithDecryption=True
            )
            return response['Parameter']['Value']
        except Exception as e:
            print(f"Error retrieving parameter {parameter_name}: {str(e)}")
            return default


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
            'AWS_REGION': 'ap-south-1',
            'LOG_LEVEL': 'DEBUG',
            'API_KEY_REQUIRED': False
            
        },
        'dev-cloud': {
            'DEBUG': True,
            'PORT': '8080',
            'DATA_DIR': 'data',
            'DB_HOST': 'dev-aurora-cluster.cluster-xyz.ap-south-1.rds.amazonaws.com',
            'DB_PORT': 5432,
            'DB_NAME': 'hospital_data_dev',
            'DB_USER': 'dev_user',
            'DB_PASSWORD': os.getenv('DEV_DB_PASSWORD', 'dev_password'),
            'USE_S3': True,
            'S3_BUCKET': 'hospital-data-chatbot-dev',
            'AWS_REGION': 'ap-south-1',
            'LOG_LEVEL': 'DEBUG',
            'API_KEY_REQUIRED': True
            # 'DB_PASSWORD': get_ssm_parameter(f"/{PROJECT_NAME}/dev-cloud/db-password", "dev_password"),            
        },
        'stage': {
            'DEBUG': False,
            'PORT': '8080',
            'DATA_DIR': 'data',
            'DB_HOST': 'stage-aurora-cluster.cluster-xyz.ap-south-1.rds.amazonaws.com',
            'DB_PORT': 5432,
            'DB_NAME': 'hospital_data_stage',
            'DB_USER': 'stage_user',
            'DB_PASSWORD': os.getenv('STAGE_DB_PASSWORD', 'stage_password'),
            'USE_S3': True,
            'S3_BUCKET': 'hospital-data-chatbot-stage',
            'AWS_REGION': 'ap-south-1',
            'LOG_LEVEL': 'INFO',
            'API_KEY_REQUIRED': True
            # 'DB_PASSWORD': get_ssm_parameter(f"/{PROJECT_NAME}/stage/db-password", "stage_password"),

        },
        'prod': {
            'DEBUG': False,
            'PORT': '8080',
            'DATA_DIR': 'data',
            'DB_HOST': 'prod-aurora-cluster.cluster-xyz.ap-south-1.rds.amazonaws.com',
            'DB_PORT': 5432,
            'DB_NAME': 'hospital_data_prod',
            'DB_USER': 'prod_user',
            'DB_PASSWORD': os.getenv('PROD_DB_PASSWORD', 'change_this_in_prod'),
            'USE_S3': True,
            'S3_BUCKET': 'hospital-data-chatbot-prod',
            'AWS_REGION': 'ap-south-1',
            'LOG_LEVEL': 'WARNING',
            'API_KEY_REQUIRED': True
            # 'DB_PASSWORD': get_ssm_parameter(f"/{PROJECT_NAME}/prod/db-password", "change_this_in_prod"),
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
            'dev-cloud': 'Development (Cloud)',
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