import os
import shutil
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import polars as pl

from app.config.settings import ETLConfig
from app.utils.logging import get_logger

logger = get_logger(__name__)

class FileHandler:
    """Cloud-compatible file operations for ETL processes."""
    
    def __init__(self):
        self.config = ETLConfig()
        self.is_cloud_mode = self.config.is_cloud_mode()
        
        if self.is_cloud_mode:
            try:
                self.s3_client = boto3.client('s3', region_name=self.config.AWS_REGION)
                logger.info(f"Initialized S3 client for region: {self.config.AWS_REGION}")
            except NoCredentialsError:
                logger.error("AWS credentials not found. Please configure AWS credentials.")
                raise
        else:
            self.s3_client = None
            # Ensure local directories exist
            self._ensure_local_directories()

    def _ensure_local_directories(self):
        """Create local directories if they don't exist."""
        directories = [
            self.config.LOCAL_DATA_DIR,
            self.config.PROCESSED_DATA_DIR,
            self.config.ARCHIVE_DATA_DIR,
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")

    def list_input_files(self, pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available input files.
        
        Args:
            pattern: File pattern to match (e.g., '*.xlsx')
            
        Returns:
            List of file information dictionaries
        """
        pattern = pattern or self.config.FILE_PATTERN
        
        if self.is_cloud_mode:
            return self._list_s3_files(
                bucket=self.config.S3_BUCKET,
                prefix=self.config.INPUT_S3_PREFIX,
                pattern=pattern
            )
        else:
            return self._list_local_files(
                directory=self.config.LOCAL_DATA_DIR,
                pattern=pattern
            )

    def _list_s3_files(self, bucket: str, prefix: str, pattern: str) -> List[Dict[str, Any]]:
        """List files in S3 bucket."""
        files = []
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        filename = os.path.basename(key)
                        
                        # Simple pattern matching (could be enhanced with regex)
                        if self._matches_pattern(filename, pattern):
                            files.append({
                                'name': filename,
                                'path': key,
                                'size': obj['Size'],
                                'last_modified': obj['LastModified'],
                                'source': 's3',
                                'full_path': f"s3://{bucket}/{key}"
                            })
            
            logger.info(f"Found {len(files)} files in S3 bucket {bucket} with prefix {prefix}")
            return files
            
        except ClientError as e:
            logger.error(f"Error listing S3 files: {str(e)}")
            raise

    def _list_local_files(self, directory: str, pattern: str) -> List[Dict[str, Any]]:
        """List files in local directory."""
        files = []
        search_pattern = os.path.join(directory, pattern)
        
        for file_path in glob.glob(search_pattern):
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                files.append({
                    'name': os.path.basename(file_path),
                    'path': file_path,
                    'size': stat.st_size,
                    'last_modified': datetime.fromtimestamp(stat.st_mtime),
                    'source': 'local',
                    'full_path': file_path
                })
        
        logger.info(f"Found {len(files)} files in local directory {directory}")
        return files

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Simple pattern matching (could be enhanced with regex)."""
        import fnmatch
        return fnmatch.fnmatch(filename, pattern)

    def read_excel_file(self, file_info: Dict[str, Any]) -> Dict[str, pl.DataFrame]:
        """
        Read Excel file and return DataFrames for each sheet.
        
        Args:
            file_info: File information dictionary from list_input_files()
            
        Returns:
            Dictionary with sheet names as keys and DataFrames as values
        """
        logger.info(f"Reading Excel file: {file_info['name']}")
        
        if file_info['source'] == 's3':
            return self._read_excel_from_s3(file_info)
        else:
            return self._read_excel_from_local(file_info)

    def _read_excel_from_s3(self, file_info: Dict[str, Any]) -> Dict[str, pl.DataFrame]:
        """Read Excel file from S3."""
        try:
            # Download file to temporary location
            temp_file = f"/tmp/{file_info['name']}"
            
            self.s3_client.download_file(
                Bucket=self.config.S3_BUCKET,
                Key=file_info['path'],
                Filename=temp_file
            )
            
            logger.debug(f"Downloaded S3 file to: {temp_file}")
            
            # Read Excel file
            sheets = self._read_excel_sheets(temp_file)
            
            # Clean up temporary file
            os.remove(temp_file)
            
            return sheets
            
        except Exception as e:
            logger.error(f"Error reading Excel from S3: {str(e)}")
            raise

    def _read_excel_from_local(self, file_info: Dict[str, Any]) -> Dict[str, pl.DataFrame]:
        """Read Excel file from local filesystem."""
        return self._read_excel_sheets(file_info['path'])

    def _read_excel_sheets(self, file_path: str) -> Dict[str, pl.DataFrame]:
        """Read all sheets from Excel file."""
        sheets = {}
        
        try:
            # Try Polars first
            try:
                # Note: Polars may not support all Excel features, so we have a pandas fallback
                sheets['Patient Details'] = pl.read_excel(file_path, sheet_name="Patient Details")
                sheets['Diagnosis Details'] = pl.read_excel(file_path, sheet_name="Diagnosis Details")
                logger.info("Successfully read Excel file with Polars")
            except Exception as polars_error:
                logger.warning(f"Polars Excel read failed: {polars_error}. Trying pandas fallback.")
                
                # Pandas fallback
                import pandas as pd
                with pd.ExcelFile(file_path) as xls:
                    for sheet_name in ['Patient Details', 'Diagnosis Details']:
                        if sheet_name in xls.sheet_names:
                            df_pandas = pd.read_excel(xls, sheet_name=sheet_name)
                            sheets[sheet_name] = pl.from_pandas(df_pandas)
                        else:
                            logger.warning(f"Sheet '{sheet_name}' not found in Excel file")
                
                logger.info("Successfully read Excel file with pandas fallback")
            
            return sheets
            
        except Exception as e:
            logger.error(f"Error reading Excel sheets from {file_path}: {str(e)}")
            raise

    def move_to_processed(self, file_info: Dict[str, Any]) -> str:
        """
        Move file to processed directory/prefix.
        
        Args:
            file_info: File information dictionary
            
        Returns:
            New file path/key
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        processed_name = f"{timestamp}_{file_info['name']}"
        
        if file_info['source'] == 's3':
            return self._move_s3_file(
                source_key=file_info['path'],
                dest_prefix=self.config.PROCESSED_S3_PREFIX,
                new_name=processed_name
            )
        else:
            return self._move_local_file(
                source_path=file_info['path'],
                dest_dir=self.config.PROCESSED_DATA_DIR,
                new_name=processed_name
            )

    def move_to_archive(self, file_info: Dict[str, Any]) -> str:
        """Move file to archive directory/prefix."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archived_name = f"{timestamp}_{file_info['name']}"
        
        if file_info['source'] == 's3':
            return self._move_s3_file(
                source_key=file_info['path'],
                dest_prefix=self.config.ARCHIVE_S3_PREFIX,
                new_name=archived_name
            )
        else:
            return self._move_local_file(
                source_path=file_info['path'],
                dest_dir=self.config.ARCHIVE_DATA_DIR,
                new_name=archived_name
            )

    def _move_s3_file(self, source_key: str, dest_prefix: str, new_name: str) -> str:
        """Move file within S3 bucket."""
        dest_key = f"{dest_prefix}{new_name}"
        
        try:
            # Copy file to new location
            copy_source = {'Bucket': self.config.S3_BUCKET, 'Key': source_key}
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.config.S3_BUCKET,
                Key=dest_key
            )
            
            # Delete original file
            self.s3_client.delete_object(
                Bucket=self.config.S3_BUCKET,
                Key=source_key
            )
            
            logger.info(f"Moved S3 file from {source_key} to {dest_key}")
            return f"s3://{self.config.S3_BUCKET}/{dest_key}"
            
        except ClientError as e:
            logger.error(f"Error moving S3 file: {str(e)}")
            raise

    def _move_local_file(self, source_path: str, dest_dir: str, new_name: str) -> str:
        """Move local file."""
        dest_path = os.path.join(dest_dir, new_name)
        
        try:
            shutil.move(source_path, dest_path)
            logger.info(f"Moved local file from {source_path} to {dest_path}")
            return dest_path
            
        except Exception as e:
            logger.error(f"Error moving local file: {str(e)}")
            raise

    def backup_file(self, file_info: Dict[str, Any]) -> Optional[str]:
        """Create a backup of the file before processing."""
        if not self.config.BACKUP_FILES:
            return None
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{timestamp}_{file_info['name']}"
        
        if file_info['source'] == 's3':
            backup_prefix = f"{self.config.INPUT_S3_PREFIX}backups/"
            return self._copy_s3_file(
                source_key=file_info['path'],
                dest_key=f"{backup_prefix}{backup_name}"
            )
        else:
            backup_dir = os.path.join(self.config.LOCAL_DATA_DIR, 'backups')
            Path(backup_dir).mkdir(exist_ok=True)
            return self._copy_local_file(
                source_path=file_info['path'],
                dest_path=os.path.join(backup_dir, backup_name)
            )

    def _copy_s3_file(self, source_key: str, dest_key: str) -> str:
        """Copy file in S3."""
        try:
            copy_source = {'Bucket': self.config.S3_BUCKET, 'Key': source_key}
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.config.S3_BUCKET,
                Key=dest_key
            )
            logger.debug(f"Created S3 backup: {dest_key}")
            return f"s3://{self.config.S3_BUCKET}/{dest_key}"
        except ClientError as e:
            logger.error(f"Error creating S3 backup: {str(e)}")
            raise

    def _copy_local_file(self, source_path: str, dest_path: str) -> str:
        """Copy local file."""
        try:
            shutil.copy2(source_path, dest_path)
            logger.debug(f"Created local backup: {dest_path}")
            return dest_path
        except Exception as e:
            logger.error(f"Error creating local backup: {str(e)}")
            raise

    def get_file_stats(self) -> Dict[str, Any]:
        """Get statistics about files in different locations."""
        stats = {
            'input_files': 0,
            'processed_files': 0,
            'archived_files': 0,
            'total_size_mb': 0,
        }
        
        try:
            # Count input files
            input_files = self.list_input_files()
            stats['input_files'] = len(input_files)
            stats['total_size_mb'] = sum(f['size'] for f in input_files) / (1024 * 1024)
            
            # Count processed files
            if self.is_cloud_mode:
                processed_files = self._list_s3_files(
                    bucket=self.config.S3_BUCKET,
                    prefix=self.config.PROCESSED_S3_PREFIX,
                    pattern='*'
                )
                archived_files = self._list_s3_files(
                    bucket=self.config.S3_BUCKET,
                    prefix=self.config.ARCHIVE_S3_PREFIX,
                    pattern='*'
                )
            else:
                processed_files = self._list_local_files(
                    directory=self.config.PROCESSED_DATA_DIR,
                    pattern='*'
                )
                archived_files = self._list_local_files(
                    directory=self.config.ARCHIVE_DATA_DIR,
                    pattern='*'
                )
            
            stats['processed_files'] = len(processed_files)
            stats['archived_files'] = len(archived_files)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting file stats: {str(e)}")
            return stats