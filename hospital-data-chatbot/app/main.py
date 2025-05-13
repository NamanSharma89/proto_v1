from fastapi import FastAPI
from app.api.routes import router as api_router
from app.core.data_processor import DataProcessor
from app.core.sql_query_engine import SQLQueryEngine
from app.utils.logging import setup_logging
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import AppConfig
import os

def create_app():
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Hospital Data Chatbot",
        description="AI-powered analysis of hospital patient data",
        version="0.1.0"
    )
    
    # Set up logging
    logger = setup_logging(log_to_file=True)
    logger.info(f"Starting application in {AppConfig.get_environment_name()} environment")
    
    # Initialize data processor and load data
    data_processor = DataProcessor(auto_ingest_db=not AppConfig.is_production())
    app.state.data_processor = data_processor
    
    # Initialize SQL query engine
    sql_query_engine = SQLQueryEngine()
    app.state.sql_query_engine = sql_query_engine
    logger.info("SQL Query Engine initialized")
    
    # Include API routes
    app.include_router(api_router, prefix="/api")
    
    # Middleware for CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not AppConfig.is_production() else ["https://your-production-domain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Apply environment-specific configurations
    if AppConfig.is_development():
        logger.debug("Development-specific configuration applied")
        
        # Add development routes if in development environment
        from app.api.dev_routes import router as dev_router
        app.include_router(dev_router, prefix="/dev")
        logger.debug("Development routes added")
    else:
        # Production & staging settings
        logger.info("Production/Staging configuration applied")

    # In the create_app function in app/main.py
    # Update data processor initialization

    # Initialize data processor and load data
    if os.path.exists(os.path.join(AppConfig.DATA_DIR, 'raw', 'hospital_data.xlsx')):
        data_processor = DataProcessor(auto_ingest_db=not AppConfig.is_production())
    else:
        logger.warning("Hospital data file not found, skipping auto-loading")
        # Initialize without auto-loading
        data_processor = DataProcessor(auto_load=False, auto_ingest_db=False)

    app.state.data_processor = data_processor
    
    logger.info("FastAPI application configured and ready")
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)