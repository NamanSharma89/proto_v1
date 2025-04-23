from fastapi import FastAPI
from app.api.routes import router as api_router
from app.core.data_processor import DataProcessor
from app.utils.logging import setup_logging
from fastapi.middleware.cors import CORSMiddleware

def create_app():
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Hospital Data Chatbot",
        description="AI-powered analysis of hospital patient data",
        version="0.1.0"
    )
    
    # Initialize data processor and load data
    data_processor = DataProcessor()
    app.state.data_processor = data_processor
    
    # Include API routes
    app.include_router(api_router, prefix="/api")

    # Set up logging
    logger = setup_logging(log_to_file=True)
    logger.info("FastAPI application started")

    # Middleware for CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for CORS
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)