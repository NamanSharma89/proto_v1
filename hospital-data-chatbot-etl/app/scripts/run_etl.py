#!/usr/bin/env python3
"""
ETL execution script for hospital data processing.
Can be run standalone or called from other systems.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.settings import ETLConfig
from app.core.etl_orchestrator import ETLOrchestrator
from app.utils.logging import setup_logging, get_logger

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Run Hospital Data ETL Process",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  ETL_ENV              - Environment (dev_local, dev_cloud, stage, prod)
  DATA_SOURCE_TYPE     - Data source type (local_file, s3)
  INPUT_S3_BUCKET      - S3 bucket for input files (cloud mode)
  DB_HOST              - Database host
  DB_PASSWORD          - Database password
  ENABLE_NOTIFICATIONS - Enable notifications (true/false)
  
Examples:
  # Run in local development mode
  ETL_ENV=dev_local python scripts/run_etl.py
  
  # Run in cloud mode with specific bucket
  ETL_ENV=dev_cloud INPUT_S3_BUCKET=my-bucket python scripts/run_etl.py
  
  # Run with file pattern and max files
  python scripts/run_etl.py --pattern "hospital_data_*.xlsx" --max-files 5
  
  # Dry run to test configuration
  python scripts/run_etl.py --dry-run
  
  # Output results as JSON
  python scripts/run_etl.py --output-json
        """
    )
    
    parser.add_argument(
        '--pattern',
        type=str,
        help='File pattern to match (overrides config default)'
    )
    
    parser.add_argument(
        '--max-files',
        type=int,
        help='Maximum number of files to process (for testing)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration and list files without processing'
    )
    
    parser.add_argument(
        '--output-json',
        action='store_true',
        help='Output results in JSON format'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Override log level'
    )
    
    parser.add_argument(
        '--config-check',
        action='store_true',
        help='Check configuration and exit'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = args.log_level if args.log_level else None
    logger = setup_logging(log_level=log_level, log_to_file=True)
    
    # Print environment info
    logger.info(f"ETL Environment: {ETLConfig.get_environment_name()}")
    logger.info(f"Cloud mode: {ETLConfig.is_cloud_mode()}")
    logger.info(f"Data source config: {ETLConfig.get_data_source_config()}")
    
    try:
        # Configuration check
        if args.config_check:
            validation_result = ETLConfig.validate_config()
            
            if args.output_json:
                print(json.dumps(dry_run_result, indent=2))
            else:
                print(f"🧪 DRY RUN RESULTS")
                print(f"Environment: {dry_run_result['environment']}")
                print(f"Files found: {dry_run_result['files_found']}")
                print(f"Parallel processing: {dry_run_result['config_summary']['parallel_processing']}")
                
                if dry_run_result['files']:
                    print("\nFiles that would be processed:")
                    for file_info in dry_run_result['files']:
                        print(f"  📄 {file_info['name']} ({file_info['size_mb']} MB, {file_info['source']})")
                else:
                    print("\n⚠️  No files found matching the pattern")
            
            sys.exit(0)
        
        # Run actual ETL
        logger.info("🚀 Starting ETL processing...")
        
        result = orchestrator.run_etl(
            file_pattern=args.pattern,
            max_files=args.max_files
        )
        
        # Output results
        if args.output_json:
            # Convert datetime objects to ISO strings for JSON serialization
            json_result = {
                'run_id': result['run_id'],
                'status': result['status'],
                'start_time': result['start_time'].isoformat() if result['start_time'] else None,
                'end_time': result['end_time'].isoformat() if result['end_time'] else None,
                'duration_seconds': result['duration_seconds'],
                'files_processed': result['files_processed'],
                'files_failed': result['files_failed'],
                'records_processed': result['records_processed'],
                'records_failed': result['records_failed'],
                'error_count': len(result['errors']),
                'warning_count': len(result['warnings']),
                'environment': ETLConfig.get_environment_name(),
                'timestamp': datetime.now().isoformat()
            }
            print(json.dumps(json_result, indent=2))
        else:
            # Human-readable output
            print(f"\n📊 ETL RESULTS")
            print(f"Run ID: {result['run_id']}")
            print(f"Status: {get_status_emoji(result['status'])} {result['status']}")
            print(f"Duration: {result['duration_seconds']:.2f} seconds")
            print(f"Files processed: {result['files_processed']}")
            print(f"Files failed: {result['files_failed']}")
            print(f"Records processed: {result['records_processed']:,}")
            
            if result['errors']:
                print(f"\n❌ Errors ({len(result['errors'])}):")
                for error in result['errors'][:5]:  # Show first 5 errors
                    print(f"  - {error.get('file', 'General')}: {error.get('message', 'Unknown error')}")
                if len(result['errors']) > 5:
                    print(f"  ... and {len(result['errors']) - 5} more errors")
            
            if result['warnings']:
                print(f"\n⚠️  Warnings ({len(result['warnings'])}):")
                for warning in result['warnings'][:3]:  # Show first 3 warnings
                    print(f"  - {warning}")
                if len(result['warnings']) > 3:
                    print(f"  ... and {len(result['warnings']) - 3} more warnings")
        
        # Determine exit code
        if result['status'] in ['completed_success', 'completed_no_files']:
            logger.info("✅ ETL completed successfully")
            sys.exit(0)
        elif result['status'] == 'completed_partial':
            logger.warning("⚠️  ETL completed with some failures")
            sys.exit(0)  # Still exit successfully if some files processed
        else:
            logger.error("❌ ETL failed")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("ETL interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    
    except Exception as e:
        logger.error(f"ETL execution failed: {str(e)}", exc_info=True)
        
        if args.output_json:
            error_result = {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'environment': ETLConfig.get_environment_name()
            }
            print(json.dumps(error_result, indent=2))
        else:
            print(f"\n❌ ETL FAILED: {str(e)}")
        
        sys.exit(1)

def get_status_emoji(status: str) -> str:
    """Get emoji for status display."""
    status_emojis = {
        'completed_success': '✅',
        'completed_partial': '⚠️',
        'completed_no_files': '📭',
        'completed_failed': '❌',
        'failed': '❌',
        'running': '🔄',
        'initialized': '🔧'
    }
    return status_emojis.get(status, '❓')

if __name__ == "__main__":
    main().output_json:
                print(json.dumps(validation_result, indent=2))
            else:
                print(f"Configuration Status: {'✅ Valid' if validation_result['valid'] else '❌ Invalid'}")
                
                if validation_result['issues']:
                    print("\nIssues:")
                    for issue in validation_result['issues']:
                        print(f"  ❌ {issue}")
                
                if validation_result['warnings']:
                    print("\nWarnings:")
                    for warning in validation_result['warnings']:
                        print(f"  ⚠️  {warning}")
            
            sys.exit(0 if validation_result['valid'] else 1)
        
        # Validate configuration before proceeding
        config_validation = ETLConfig.validate_config()
        if not config_validation['valid']:
            logger.error("Configuration validation failed:")
            for issue in config_validation['issues']:
                logger.error(f"  - {issue}")
            sys.exit(1)
        
        if config_validation['warnings']:
            for warning in config_validation['warnings']:
                logger.warning(warning)
        
        # Initialize orchestrator
        orchestrator = ETLOrchestrator()
        
        # Handle dry run
        if args.dry_run:
            logger.info("🧪 DRY RUN MODE - No files will be processed")
            
            from app.utils.file_handlers import FileHandler
            file_handler = FileHandler()
            
            # List files that would be processed
            input_files = file_handler.list_input_files(pattern=args.pattern)
            
            dry_run_result = {
                'mode': 'dry_run',
                'timestamp': datetime.now().isoformat(),
                'environment': ETLConfig.get_environment_name(),
                'files_found': len(input_files),
                'files': [
                    {
                        'name': f['name'],
                        'size_mb': round(f['size'] / (1024 * 1024), 2),
                        'last_modified': f['last_modified'].isoformat() if hasattr(f['last_modified'], 'isoformat') else str(f['last_modified']),
                        'source': f['source']
                    }
                    for f in input_files
                ],
                'config_summary': {
                    'data_source': ETLConfig.get_data_source_config(),
                    'parallel_processing': ETLConfig.PARALLEL_PROCESSING,
                    'max_workers': ETLConfig.MAX_WORKERS,
                    'notifications_enabled': ETLConfig.ENABLE_NOTIFICATIONS
                }
            }