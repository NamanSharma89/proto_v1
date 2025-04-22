# app/config/settings.py
import os

class AppConfig:
    """Application configuration settings."""
    
    # App settings
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    PORT = os.getenv('PORT', '8080')
    
    # Data settings
    DATA_DIR = os.getenv('DATA_DIR', 'data')
    
    # AWS settings
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    USE_S3 = os.getenv('USE_S3', 'False') == 'True'
    S3_BUCKET = os.getenv('S3_BUCKET', 'hospital-data-chatbot')
    
    # Database settings
    DB_HOST = os.getenv('DB_HOST', 'your-aurora-endpoint.us-east-1.rds.amazonaws.com')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'hospital_data')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'your-password')
    
    # Bedrock settings
    BEDROCK_MODEL_ID = os.getenv(
        'BEDROCK_MODEL_ID', 
        'anthropic.claude-3-sonnet-20240229-v1:0'
    )
    
    # Security settings
    API_KEY_REQUIRED = os.getenv('API_KEY_REQUIRED', 'True') == 'True'
    API_KEY = os.getenv('API_KEY', 'default_dev_key')  # Change in production!