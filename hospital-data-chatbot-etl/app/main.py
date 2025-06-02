import sys
import argparse
from datetime import datetime
from typing import Optional

from fastapi import FastAPI
import uvicorn

from app.config.settings import ETLConfig
from app.core.etl_orchestrator import ETLOrchestrator
from app.utils.logging import setup_logging, get_logger
from app.api.routes import router as api_router

def create_app() -> FastAPI:
    """Create FastAPI application for ETL monitoring (optional)."""
    app = FastAPI(
        title="Hospital Data ETL",
        description="ETL service for hospital patient data processing",
        version="0.1.0"
    )
    
    # Set up logging
    logger = setup_logging(log_to_file=True)
    logger.info(f"Starting ETL service in {ETLConfig.get_environment_name()} environment")
    
    # Validate configuration
    config_validation = ETLConfig.validate_config()
    if not config_validation['valid']:
        logger.error(f"Configuration validation failed: {config_validation['issues']}")
        sys.exit(1)
    
    if config_validation['warnings']:
        for warning in config_validation['warnings']:
            logger.warning(warning)
    
    # Include API routes if enabled
    if ETLConfig.ENABLE_API:
        app.include_router(api_router, prefix="/api/v1")
        logger.info("ETL API endpoints enabled")
    else:
        logger.info("ETL API endpoints disabled")
    
    return app

def run_etl_batch(
    file_pattern: Optional[str] = None,
    max_files: Optional[int] = None,
    dry_run: bool = False
) -> int:
    """
    Run ETL in batch mode.
    
    Args:
        file_pattern: File pattern to match
        max_files: Maximum number of files to process
        dry_run: If True, only validate configuration and list files
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger = get_logger(__name__)
    logger.info("Starting ETL batch processing")
    
    try:
        orchestrator = ETLOrchestrator()
        
        if dry_run:
            logger.info("DRY RUN MODE - No files will be processed")
            
            # Validate configuration
            config_validation = ETLConfig.validate_config()
            if not config_validation['valid']:
                logger.error(f"Configuration validation failed: {config_validation['issues']}")
                return 1
            
            # List available files
            from app.utils.file_handlers import FileHandler
            file_handler = FileHandler()
            input_files = file_handler.list_input_files(pattern=file_pattern)
            
            logger.info(f"Found {len(input_files)} files that would be processed:")
            for file_info in input_files:
                logger.info(f"  - {file_info['name']} ({file_info['size']} bytes)")
            
            return 0
        
        # Run actual ETL
        result = orchestrator.run_etl(
            file_pattern=file_pattern,
            max_files=max_files
        )
        
        # Determine exit code based on result
        if result['status'] in ['completed_success', 'completed_no_files']:
            return 0
        elif result['status'] == 'completed_partial':
            logger.warning("ETL completed with some failures")
            return 0  # Still consider success if some files processed
        else:
            logger.error("ETL failed")
            return 1
            
    except Exception as e:
        logger.error(f"ETL batch processing failed: {str(e)}", exc_info=True)
        return 1

def run_api_server():
    """Run ETL service in API server mode."""
    logger = get_logger(__name__)
    
    if not ETLConfig.ENABLE_API:
        logger.error("API mode requested but ENABLE_API is False in configuration")
        sys.exit(1)
    
    app = create_app()
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=ETLConfig.API_PORT,
        log_level=ETLConfig.LOG_LEVEL.lower(),
        reload=ETLConfig.DEBUG
    )

def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Hospital Data ETL Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run ETL in batch mode
  python -m app.main batch

  # Run ETL with file pattern
  python -m app.main batch --pattern "*.xlsx"
  
  # Run ETL with max files limit (for testing)
  python -m app.main batch --max-files 1
  
  # Dry run to validate config and list files
  python -m app.main batch --dry-run
  
  # Run API server for monitoring
  python -m app.main server
  
  # Run scheduled ETL (see schedule_etl.py)
  python scripts/schedule_etl.py
        """
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest='mode', help='ETL mode')
    
    # Batch mode
    batch_parser = subparsers.add_parser('batch', help='Run ETL in batch mode')
    batch_parser.add_argument(
        '--pattern', 
        type=str, 
        help='File pattern to match (e.g., "*.xlsx")'
    )
    batch_parser.add_argument(
        '--max-files', 
        type=int, 
        help='Maximum number of files to process (for testing)'
    )
    batch_parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='Validate configuration and list files without processing'
    )
    
    # Server mode
    server_parser = subparsers.add_parser('server', help='Run ETL API server')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        sys.exit(1)
    
    # Set up basic logging for argument parsing
    setup_logging()
    
    if args.mode == 'batch':
        exit_code = run_etl_batch(
            file_pattern=args.pattern,
            max_files=args.max_files,
            dry_run=args.dry_run
        )
        sys.exit(exit_code)
    
    elif args.mode == 'server':
        run_api_server()
    
    else:
        print(f"Unknown mode: {args.mode}")
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()