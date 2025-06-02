# app/utils/aws.py
import boto3
import io
import os
from botocore.exceptions import ClientError
from app.config.settings import AppConfig
import logging

# Set up logger
logger = logging.getLogger(__name__)

def get_s3_client():
    """
    Create and return an S3 client.
    
    Uses AWS credentials from environment variables or IAM role.
    """
    return boto3.client(
        's3',
        region_name=AppConfig.AWS_REGION
    )

def upload_to_s3(df, bucket_name, object_key):
    """
    Upload a dataframe to S3 as a CSV file.
    
    Args:
        df: A pandas or polars dataframe to upload
        bucket_name: S3 bucket name
        object_key: S3 object key (path/filename.csv)
        
    Returns:
        S3 URI of the uploaded file
    """
    try:
        # Create S3 client
        s3_client = get_s3_client()
        
        # Convert dataframe to CSV in memory
        csv_buffer = io.BytesIO()
        
        # Handle both pandas and polars dataframes
        if hasattr(df, 'to_csv'):  # pandas DataFrame
            df.to_csv(csv_buffer, index=False)
        else:  # polars DataFrame
            # Convert to pandas first if needed
            if hasattr(df, 'to_pandas'):
                df.to_pandas().to_csv(csv_buffer, index=False)
            else:
                # Write to a temporary file then read it back
                temp_path = '/tmp/temp_csv.csv'
                df.write_csv(temp_path)
                with open(temp_path, 'rb') as f:
                    csv_buffer.write(f.read())
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        # Reset buffer position
        csv_buffer.seek(0)
        
        # Upload to S3
        s3_client.upload_fileobj(
            csv_buffer,
            bucket_name,
            object_key,
            ExtraArgs={
                'ContentType': 'text/csv'
            }
        )
        
        logger.info(f"File uploaded successfully to s3://{bucket_name}/{object_key}")
        
        # Return the S3 URI
        return f"s3://{bucket_name}/{object_key}"
    
    except ClientError as e:
        logger.error(f"Error uploading to S3: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during S3 upload: {e}")
        raise

def download_from_s3(bucket_name, object_key, local_path=None):
    """
    Download a file from S3.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        local_path: Local path to save the file (optional)
        
    Returns:
        Local path of the downloaded file or file content as bytes
    """
    try:
        # Create S3 client
        s3_client = get_s3_client()
        
        if local_path:
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download to file
            s3_client.download_file(bucket_name, object_key, local_path)
            logger.info(f"File downloaded from S3 to {local_path}")
            return local_path
        else:
            # Download to memory
            buffer = io.BytesIO()
            s3_client.download_fileobj(bucket_name, object_key, buffer)
            buffer.seek(0)
            logger.info(f"File downloaded from S3 to memory")
            return buffer.read()
    
    except ClientError as e:
        logger.error(f"Error downloading from S3: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during S3 download: {e}")
        raise