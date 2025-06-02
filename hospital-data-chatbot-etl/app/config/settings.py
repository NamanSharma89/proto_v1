import os
from typing import Dict, Any, Optional
import boto3

class ETLConfig:
    """ETL-specific configuration settings with cloud compatibility."""

    # Environment selection
    ENV = os.getenv('ETL_ENV', 'dev_local')  # Options: dev_local, dev_cloud, stage, prod

    # ETL-specific settings
    ETL_MODE = os.getenv('ETL_MODE', 'batch')  # Options: batch, streaming, scheduled
    ETL_SCHEDULE = os.getenv('ETL_SCHEDULE', '0 2 * * *')  # Daily at 2 AM
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '1000'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '60'))  # seconds

    # Data source configurations
    DATA_SOURCE_TYPE = os.getenv('DATA_SOURCE_TYPE', 'local_file')  # local_file, s3, sftp, api
    
    # Local file settings
    LOCAL_DATA_DIR = os.getenv('LOCAL_DATA_DIR', 'data/input')
    PROCESSED_DATA_DIR = os.getenv('PROCESSED_DATA_DIR', 'data/processed')
    ARCHIVE_DATA_DIR = os.getenv('ARCHIVE_DATA_DIR', 'data/archive')
    
    # Cloud storage settings
    INPUT_S3_BUCKET = os.getenv('INPUT_S3_BUCKET')
    INPUT_S3_PREFIX = os.getenv('INPUT_S3_PREFIX', 'hospital-data/input/')
    PROCESSED_S3_PREFIX = os.getenv('PROCESSED_S3_PREFIX', 'hospital-data/processed/')
    ARCHIVE_S3_PREFIX = os.getenv('ARCHIVE_S3_PREFIX', 'hospital-data/archive/')
    
    # File patterns
    FILE_PATTERN = os.getenv('FILE_PATTERN', 'hospital_data*.xlsx')
    BACKUP_FILES = os.getenv('BACKUP_FILES', 'true').lower() == 'true'
    
    # Notification settings
    ENABLE_NOTIFICATIONS = os.getenv('ENABLE_NOTIFICATIONS', 'false').lower() == 'true'
    SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')
    SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
    
    # Monitoring settings
    ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'false').lower() == 'true'
    CLOUDWATCH_NAMESPACE = os.getenv('CLOUDWATCH_NAMESPACE', 'HospitalETL')

    # Environment-specific configurations
    _env_configs: Dict[str, Dict[str, Any]] = {
        'dev_local': {
            'DEBUG': True,
            'API_PORT': '8081',  # Different port from main API
            'DATA_DIR': 'data',
            'DB_HOST': 'localhost',
            'DB_PORT': 5432,
            'DB_NAME': 'hospital_data_etl',
            'DB_USER': 'postgres',
            'DB_PASSWORD': 'postgres',
            'USE_S3': False,
            'USE_CLOUD_STORAGE': False,
            'AWS_REGION': 'ap-south-1',
            'LOG_LEVEL': 'DEBUG',
            'ENABLE_API': True,  # Enable API for monitoring
            'PARALLEL_PROCESSING': False,
            'MAX_WORKERS': 1,
        },
        'dev_cloud': {
            'DEBUG': True,
            'API_PORT': '8081',
            'DATA_DIR': '/tmp/etl_data',
            'DB_HOST': 'dev-aurora-cluster.cluster-xyz.ap-south-1.rds.amazonaws.com',
            'DB_PORT': 5432,
            'DB_NAME': 'hospital_data_dev',
            'DB_USER': 'etl_user',
            'DB_PASSWORD': os.getenv('DEV_ETL_DB_PASSWORD', 'dev_etl_password'),
            'USE_S3': True,
            'USE_CLOUD_STORAGE': True,
            'S3_BUCKET': 'hospital-data-chatbot-dev-etl',
            'AWS_REGION': 'ap-south-1',
            'LOG_LEVEL': 'DEBUG',
            'ENABLE_API': True,
            'PARALLEL_PROCESSING': True,
            'MAX_WORKERS': 2,
            'ENABLE_NOTIFICATIONS': True,
        },
        'stage': {
            'DEBUG': False,
            'API_PORT': '8081',
            'DATA_DIR': '/app/data',
            'DB_HOST': 'stage-aurora-cluster.cluster-xyz.ap-south-1.rds.amazonaws.com',
            'DB_PORT': 5432,
            'DB_NAME': 'hospital_data_stage',
            'DB_USER': 'etl_user',
            'DB_PASSWORD': os.getenv('STAGE_ETL_DB_PASSWORD', 'stage_etl_password'),
            'USE_S3': True,
            'USE_CLOUD_STORAGE': True,
            'S3_BUCKET': 'hospital-data-chatbot-stage-etl',
            'AWS_REGION': 'ap-south-1',
            'LOG_LEVEL': 'INFO',
            'ENABLE_API': True,
            'PARALLEL_PROCESSING': True,
            'MAX_WORKERS': 4,
            'ENABLE_NOTIFICATIONS': True,
            'ENABLE_METRICS': True,
        },
        'prod': {
            'DEBUG': False,
            'API_PORT': '8081',
            'DATA_DIR': '/app/data',
            'DB_HOST': 'prod-aurora-cluster.cluster-xyz.ap-south-1.rds.amazonaws.com',
            'DB_PORT': 5432,
            'DB_NAME': 'hospital_data_prod',
            'DB_USER': 'etl_user',
            'DB_PASSWORD': os.getenv('PROD_ETL_DB_PASSWORD', 'change_this_in_prod'),
            'USE_S3': True,
            'USE_CLOUD_STORAGE': True,
            'S3_BUCKET': 'hospital-data-chatbot-prod-etl',
            'AWS_REGION': 'ap-south-1',
            'LOG_LEVEL': 'WARNING',
            'ENABLE_API': False,  # No API in production for security
            'PARALLEL_PROCESSING': True,
            'MAX_WORKERS': 8,
            'ENABLE_NOTIFICATIONS': True,
            'ENABLE_METRICS': True,
        }
    }

    # Apply environment-specific settings
    env_config = _env_configs.get(ENV, _env_configs['dev_local'])

    # Set all config values as class attributes
    for key, value in env_config.items():
        locals()[key] = value

    # Override with environment variables if they exist
    for key in env_config.keys():
        env_value = os.getenv(key)
        if env_value is not None:
            # Handle special cases for type conversion
            if key in ['DEBUG', 'USE_S3', 'USE_CLOUD_STORAGE', 'ENABLE_API', 'PARALLEL_PROCESSING', 'ENABLE_NOTIFICATIONS', 'ENABLE_METRICS']:
                locals()[key] = env_value.lower() == 'true'
            elif key in ['DB_PORT', 'API_PORT', 'MAX_WORKERS']:
                locals()[key] = int(env_value)
            else:
                locals()[key] = env_value

    # Cloud-specific settings
    if USE_CLOUD_STORAGE and not locals().get('S3_BUCKET'):
        locals()['S3_BUCKET'] = INPUT_S3_BUCKET or 'hospital-data-etl-default'

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

    @classmethod
    def is_cloud_mode(cls) -> bool:
        """Check if running in cloud mode."""
        return cls.USE_CLOUD_STORAGE or cls.ENV != 'dev_local'

    @classmethod
    def get_data_source_config(cls) -> Dict[str, Any]:
        """Get data source configuration based on environment."""
        if cls.USE_CLOUD_STORAGE:
            return {
                'type': 's3',
                'bucket': cls.S3_BUCKET,
                'input_prefix': cls.INPUT_S3_PREFIX,
                'processed_prefix': cls.PROCESSED_S3_PREFIX,
                'archive_prefix': cls.ARCHIVE_S3_PREFIX,
                'region': cls.AWS_REGION,
            }
        else:
            return {
                'type': 'local',
                'input_dir': cls.LOCAL_DATA_DIR,
                'processed_dir': cls.PROCESSED_DATA_DIR,
                'archive_dir': cls.ARCHIVE_DATA_DIR,
            }

    @classmethod
    def get_notification_config(cls) -> Dict[str, Any]:
        """Get notification configuration."""
        config = {
            'enabled': cls.ENABLE_NOTIFICATIONS,
        }
        
        if cls.ENABLE_NOTIFICATIONS:
            if cls.SNS_TOPIC_ARN:
                config['sns'] = {
                    'topic_arn': cls.SNS_TOPIC_ARN,
                    'region': cls.AWS_REGION,
                }
            
            if cls.SLACK_WEBHOOK_URL:
                config['slack'] = {
                    'webhook_url': cls.SLACK_WEBHOOK_URL,
                }
        
        return config

    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate configuration and return validation results."""
        issues = []
        warnings = []
        
        # Check required settings for cloud mode
        if cls.USE_CLOUD_STORAGE:
            if not cls.S3_BUCKET:
                issues.append("S3_BUCKET is required when USE_CLOUD_STORAGE is enabled")
            
            if not cls.AWS_REGION:
                issues.append("AWS_REGION is required for cloud mode")
        
        # Check database connection settings
        required_db_settings = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        for setting in required_db_settings:
            if not getattr(cls, setting, None):
                issues.append(f"{setting} is required")
        
        # Check notification settings
        if cls.ENABLE_NOTIFICATIONS:
            if not cls.SNS_TOPIC_ARN and not cls.SLACK_WEBHOOK_URL:
                warnings.append("ENABLE_NOTIFICATIONS is true but no notification endpoints configured")
        
        # Check production-specific settings
        if cls.is_production():
            if cls.DEBUG:
                warnings.append("DEBUG should be False in production")
            
            if cls.DB_PASSWORD == 'change_this_in_prod':
                issues.append("Default database password detected in production")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
        }