import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import polars as pl

from app.config.settings import ETLConfig
from app.core.data_processor import ETLDataProcessor
from app.utils.file_handlers import FileHandler
from app.utils.logging import get_logger
from app.utils.notifications import NotificationManager

logger = get_logger(__name__)

class ETLOrchestrator:
    """
    Main orchestrator for ETL processes.
    Handles file discovery, processing coordination, error handling, and notifications.
    """
    
    def __init__(self):
        self.config = ETLConfig()
        self.file_handler = FileHandler()
        self.data_processor = ETLDataProcessor()
        self.notification_manager = NotificationManager()
        
        self.stats = {
            'run_id': self._generate_run_id(),
            'start_time': None,
            'end_time': None,
            'duration_seconds': 0,
            'files_processed': 0,
            'files_failed': 0,
            'records_processed': 0,
            'records_failed': 0,
            'status': 'initialized',
            'errors': [],
            'warnings': []
        }
        
        logger.info(f"ETL Orchestrator initialized with run_id: {self.stats['run_id']}")

    def _generate_run_id(self) -> str:
        """Generate unique run ID for tracking."""
        return f"etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(datetime.now())) % 10000:04d}"

    def run_etl(self, file_pattern: Optional[str] = None, max_files: Optional[int] = None) -> Dict[str, Any]:
        """
        Run the complete ETL process.
        
        Args:
            file_pattern: Override default file pattern
            max_files: Limit number of files to process (for testing)
            
        Returns:
            Dictionary with run statistics and results
        """
        self.stats['start_time'] = datetime.now()
        self.stats['status'] = 'running'
        
        logger.info(f"Starting ETL run: {self.stats['run_id']}")
        
        try:
            # Validate configuration
            config_validation = self.config.validate_config()
            if not config_validation['valid']:
                raise ValueError(f"Configuration validation failed: {config_validation['issues']}")
            
            if config_validation['warnings']:
                for warning in config_validation['warnings']:
                    logger.warning(warning)
                    self.stats['warnings'].append(warning)
            
            # Discover input files
            logger.info("Discovering input files...")
            input_files = self.file_handler.list_input_files(pattern=file_pattern)
            
            if not input_files:
                logger.warning("No input files found matching the pattern")
                self.stats['status'] = 'completed_no_files'
                return self._finalize_run()
            
            if max_files:
                input_files = input_files[:max_files]
                logger.info(f"Limited processing to {len(input_files)} files for testing")
            
            logger.info(f"Found {len(input_files)} files to process")
            
            # Process files
            if self.config.PARALLEL_PROCESSING and len(input_files) > 1:
                results = self._process_files_parallel(input_files)
            else:
                results = self._process_files_sequential(input_files)
            
            # Aggregate results
            self._aggregate_results(results)
            
            # Determine final status
            if self.stats['files_failed'] == 0:
                self.stats['status'] = 'completed_success'
            elif self.stats['files_processed'] > 0:
                self.stats['status'] = 'completed_partial'
            else:
                self.stats['status'] = 'completed_failed'
            
            logger.info(f"ETL run completed: {self.stats['status']}")
            
        except Exception as e:
            logger.error(f"ETL run failed: {str(e)}", exc_info=True)
            self.stats['status'] = 'failed'
            self.stats['errors'].append({
                'type': 'orchestrator_error',
                'message': str(e),
                'traceback': traceback.format_exc(),
                'timestamp': datetime.now().isoformat()
            })
        
        return self._finalize_run()

    def _process_files_sequential(self, input_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process files one by one."""
        logger.info("Processing files sequentially")
        results = []
        
        for i, file_info in enumerate(input_files, 1):
            logger.info(f"Processing file {i}/{len(input_files)}: {file_info['name']}")
            
            try:
                result = self._process_single_file(file_info)
                results.append(result)
                
                # Add delay between files if configured
                if hasattr(self.config, 'INTER_FILE_DELAY') and self.config.INTER_FILE_DELAY > 0:
                    time.sleep(self.config.INTER_FILE_DELAY)
                    
            except Exception as e:
                logger.error(f"Failed to process file {file_info['name']}: {str(e)}")
                results.append({
                    'file_info': file_info,
                    'success': False,
                    'error': str(e),
                    'traceback': traceback.format_exc(),
                    'processing_time': 0,
                    'records_processed': 0
                })
        
        return results

    def _process_files_parallel(self, input_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process files in parallel using ThreadPoolExecutor."""
        logger.info(f"Processing files in parallel with {self.config.MAX_WORKERS} workers")
        results = []
        
        with ThreadPoolExecutor(max_workers=self.config.MAX_WORKERS) as executor:
            # Submit all files for processing
            future_to_file = {
                executor.submit(self._process_single_file, file_info): file_info 
                for file_info in input_files
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                file_info = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Completed processing: {file_info['name']}")
                except Exception as e:
                    logger.error(f"Failed to process file {file_info['name']}: {str(e)}")
                    results.append({
                        'file_info': file_info,
                        'success': False,
                        'error': str(e),
                        'traceback': traceback.format_exc(),
                        'processing_time': 0,
                        'records_processed': 0
                    })
        
        return results

    def _process_single_file(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single file through the complete ETL pipeline.
        
        Args:
            file_info: File information dictionary
            
        Returns:
            Processing result dictionary
        """
        start_time = time.time()
        result = {
            'file_info': file_info,
            'success': False,
            'processing_time': 0,
            'records_processed': 0,
            'patient_records': 0,
            'diagnosis_records': 0,
            'validation_stats': {},
            'error': None,
            'traceback': None
        }
        
        try:
            logger.info(f"Starting processing of file: {file_info['name']}")
            
            # Create backup if configured
            backup_path = self.file_handler.backup_file(file_info)
            if backup_path:
                logger.debug(f"Created backup: {backup_path}")
            
            # Read Excel file
            logger.debug("Reading Excel sheets...")
            sheets = self.file_handler.read_excel_file(file_info)
            
            if 'Patient Details' not in sheets or 'Diagnosis Details' not in sheets:
                raise ValueError("Required sheets 'Patient Details' and 'Diagnosis Details' not found")
            
            # Process data through ETL pipeline
            logger.debug("Processing data through ETL pipeline...")
            processing_result = self.data_processor.process_hospital_data(
                patient_data=sheets['Patient Details'],
                diagnosis_data=sheets['Diagnosis Details'],
                source_file=file_info['name']
            )
            
            # Update result with processing statistics
            result.update({
                'success': processing_result['success'],
                'patient_records': processing_result.get('patient_records', 0),
                'diagnosis_records': processing_result.get('diagnosis_records', 0),
                'validation_stats': processing_result.get('validation_stats', {}),
                'records_processed': (
                    processing_result.get('patient_records', 0) + 
                    processing_result.get('diagnosis_records', 0)
                )
            })
            
            if not processing_result['success']:
                raise ValueError(f"Data processing failed: {processing_result.get('error', 'Unknown error')}")
            
            # Move file to processed directory
            logger.debug("Moving file to processed location...")
            processed_path = self.file_handler.move_to_processed(file_info)
            result['processed_path'] = processed_path
            
            logger.info(f"Successfully processed file: {file_info['name']} "
                       f"({result['patient_records']} patients, {result['diagnosis_records']} diagnoses)")
            
        except Exception as e:
            logger.error(f"Error processing file {file_info['name']}: {str(e)}")
            result['error'] = str(e)
            result['traceback'] = traceback.format_exc()
            
            # Move file to archive on error (if configured)
            if hasattr(self.config, 'ARCHIVE_FAILED_FILES') and self.config.ARCHIVE_FAILED_FILES:
                try:
                    archived_path = self.file_handler.move_to_archive(file_info)
                    result['archived_path'] = archived_path
                    logger.info(f"Moved failed file to archive: {archived_path}")
                except Exception as archive_error:
                    logger.error(f"Failed to archive file: {str(archive_error)}")
        
        finally:
            result['processing_time'] = time.time() - start_time
        
        return result

    def _aggregate_results(self, results: List[Dict[str, Any]]):
        """Aggregate processing results into run statistics."""
        for result in results:
            if result['success']:
                self.stats['files_processed'] += 1
                self.stats['records_processed'] += result.get('records_processed', 0)
            else:
                self.stats['files_failed'] += 1
                self.stats['errors'].append({
                    'type': 'file_processing_error',
                    'file': result['file_info']['name'],
                    'message': result.get('error', 'Unknown error'),
                    'traceback': result.get('traceback'),
                    'timestamp': datetime.now().isoformat()
                })

    def _finalize_run(self) -> Dict[str, Any]:
        """Finalize the ETL run and send notifications."""
        self.stats['end_time'] = datetime.now()
        self.stats['duration_seconds'] = (
            self.stats['end_time'] - self.stats['start_time']
        ).total_seconds()
        
        # Send notifications
        if self.config.ENABLE_NOTIFICATIONS:
            try:
                self.notification_manager.send_etl_completion_notification(self.stats)
            except Exception as e:
                logger.error(f"Failed to send notification: {str(e)}")
        
        # Log final statistics
        logger.info(f"ETL Run Summary - ID: {self.stats['run_id']}")
        logger.info(f"  Status: {self.stats['status']}")
        logger.info(f"  Duration: {self.stats['duration_seconds']:.2f} seconds")
        logger.info(f"  Files Processed: {self.stats['files_processed']}")
        logger.info(f"  Files Failed: {self.stats['files_failed']}")
        logger.info(f"  Records Processed: {self.stats['records_processed']}")
        
        if self.stats['errors']:
            logger.warning(f"  Errors: {len(self.stats['errors'])}")
        
        if self.stats['warnings']:
            logger.warning(f"  Warnings: {len(self.stats['warnings'])}")
        
        return self.stats

    def get_run_status(self) -> Dict[str, Any]:
        """Get current run status (useful for API endpoints)."""
        return {
            'run_id': self.stats['run_id'],
            'status': self.stats['status'],
            'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
            'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None,
            'duration_seconds': self.stats['duration_seconds'],
            'files_processed': self.stats['files_processed'],
            'files_failed': self.stats['files_failed'],
            'records_processed': self.stats['records_processed'],
            'error_count': len(self.stats['errors']),
            'warning_count': len(self.stats['warnings'])
        }

    def cleanup_old_files(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Clean up old processed and archived files.
        
        Args:
            days_old: Files older than this many days will be deleted
            
        Returns:
            Cleanup statistics
        """
        logger.info(f"Starting cleanup of files older than {days_old} days")
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cleanup_stats = {
            'processed_files_deleted': 0,
            'archived_files_deleted': 0,
            'total_size_freed_mb': 0,
            'errors': []
        }
        
        try:
            # This would need implementation based on file storage type
            # For now, just log the intention
            logger.info(f"Cleanup would remove files older than {cutoff_date}")
            
            # TODO: Implement actual cleanup logic for both local and S3
            # - List files in processed/archived locations
            # - Check modification dates
            # - Delete files older than cutoff_date
            # - Track statistics
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            cleanup_stats['errors'].append(str(e))
        
        return cleanup_stats