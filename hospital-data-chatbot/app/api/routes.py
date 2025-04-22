from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()

class ChatQuery(BaseModel):
    query: str

@router.get("/health")
async def health_check():
    """API health check endpoint."""
    return {"status": "healthy", "message": "API is operational"}

@router.get("/data/stats")
async def data_stats(request: Request):
    """Get statistics about the loaded data."""
    stats = request.app.state.data_processor.get_data_stats()
    return stats

# app/api/routes.py
@router.post("/import-to-db")
async def import_to_db(request: Request):
    """Import processed data to the database. Used for nightly batch processing."""
    try:
        from app.core.db_importer import DbImporter
        
        # Get processed data
        patient_data = request.app.state.data_processor.patient_data
        diagnosis_data = request.app.state.data_processor.diagnosis_data
        
        # Import to database
        importer = DbImporter()
        try:
            result = importer.import_data(patient_data, diagnosis_data)
            return {
                "status": "success",
                "message": "Data imported successfully",
                "details": result
            }
        finally:
            importer.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import data to database: {str(e)}"
        )

@router.post("/chat")
async def chat(query: ChatQuery, request: Request):
    """Process chat requests."""
    if not query.query:
        raise HTTPException(status_code=400, detail="No query provided")
    
    # Process the query using the query engine
    from app.core.query_engine import QueryEngine
    from app.utils.calculation_handler import CalculationHandler
    
    query_engine = QueryEngine(
        request.app.state.data_processor.patient_data,
        request.app.state.data_processor.diagnosis_data
    )
    llm_response = query_engine.process_query(query.query)
    
    # Process any calculation requests in the LLM response
    calc_handler = CalculationHandler(
        request.app.state.data_processor.patient_data,
        request.app.state.data_processor.diagnosis_data
    )
    final_response = calc_handler.process_response(llm_response)
    
    return {"response": final_response}