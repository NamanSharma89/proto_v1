from fastapi import FastAPI
from app.api.routes import router as api_router
from app.core.data_processor import DataProcessor
from app.utils.logging import setup_logging
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import AppConfig


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
        # Development-only settings
    else:
        # Production & staging settings
        logger.info("Production/Staging configuration applied")
    
    logger.info("FastAPI application configured and ready")
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)