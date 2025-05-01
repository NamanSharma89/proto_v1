# app/api/sql_chat_routes.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from app.core.sql_query_engine import SQLQueryEngine
from app.config.settings import AppConfig
from app.utils.logging import get_logger
from typing import Dict, Any, Optional, List

router = APIRouter()
logger = get_logger(__name__)

class SQLChatQuery(BaseModel):
    """Model for a SQL chat query request."""
    query: str
    include_sql: bool = False
    include_reasoning: bool = False

class SQLChatResponse(BaseModel):
    """Model for a SQL chat response."""
    response: str
    success: bool
    sql: Optional[str] = None
    reasoning: Optional[str] = None
    row_count: Optional[int] = None
    execution_time_ms: Optional[float] = None
    error: Optional[str] = None

@router.post("/sql-chat", response_model=SQLChatResponse)
async def sql_chat(query_data: SQLChatQuery, request: Request) -> Dict[str, Any]:
    """
    Process a natural language query by converting it to SQL,
    executing it on the database, and returning formatted results.
    
    Args:
        query_data: The query request containing the natural language question
        
    Returns:
        Formatted response with results and optional SQL details
    """
    if not query_data.query:
        raise HTTPException(status_code=400, detail="No query provided")
    
    try:
        logger.info(f"Processing SQL chat query: {query_data.query}")
        
        # Get SQL Query Engine - initialize new one if not in app state
        if not hasattr(request.app.state, "sql_query_engine"):
            logger.info("Initializing SQL Query Engine")
            request.app.state.sql_query_engine = SQLQueryEngine()
        
        sql_query_engine = request.app.state.sql_query_engine
        
        # Process the query
        import time
        start_time = time.time()
        result = sql_query_engine.process_query(query_data.query)
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Build response based on user preferences
        response = {
            "response": result.get("response", ""),
            "success": result.get("success", False),
            "execution_time_ms": execution_time
        }
        
        # Include SQL and reasoning if requested or in debug mode
        if query_data.include_sql or AppConfig.DEBUG:
            response["sql"] = result.get("sql", None)
        
        if query_data.include_reasoning or AppConfig.DEBUG:
            response["reasoning"] = result.get("reasoning", None)
        
        # Include error if present
        if "error" in result:
            response["error"] = result["error"]
        
        # Include row count if results were returned
        if "row_count" in result:
            response["row_count"] = result["row_count"]
        
        logger.info(f"SQL chat query processed successfully in {execution_time:.2f}ms")
        return response
        
    except Exception as e:
        logger.error(f"Error processing SQL chat query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )

@router.get("/db-schema")
async def get_db_schema(request: Request) -> Dict[str, Any]:
    """
    Get database schema information.
    Only available in development environments.
    
    Returns:
        Database schema details
    """
    # Security check - only available in development
    if not AppConfig.is_development():
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only available in development environments"
        )
    
    try:
        # Get SQL Query Engine - initialize new one if not in app state
        if not hasattr(request.app.state, "sql_query_engine"):
            logger.info("Initializing SQL Query Engine")
            request.app.state.sql_query_engine = SQLQueryEngine()
        
        sql_query_engine = request.app.state.sql_query_engine
        
        # Get schema information
        if sql_query_engine.db_schema:
            return {
                "status": "success",
                "schema": sql_query_engine.db_schema
            }
        else:
            return {
                "status": "error",
                "message": "Database schema not loaded"
            }
            
    except Exception as e:
        logger.error(f"Error retrieving database schema: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve database schema: {str(e)}"
        )