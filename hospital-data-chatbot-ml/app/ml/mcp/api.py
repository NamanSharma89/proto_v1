# app/ml/mcp/api.py
from fastapi import FastAPI, HTTPException, Depends
from app.ml.mcp.protocol import ModelRequest, ModelResponse, ModelMetadata
from app.ml.mcp.service import MCPModelService
from typing import List

# Create FastAPI app
app = FastAPI(
    title="Hospital Data ML API",
    description="ML API for Hospital Data Chatbot with Model Context Protocol",
    version="1.0.0"
)

# Create MCP service
mcp_service = MCPModelService()

@app.get("/models", response_model=List[ModelMetadata])
async def get_models():
    """Get a list of available models."""
    try:
        return mcp_service.get_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/{model_id}", response_model=ModelMetadata)
async def get_model_metadata(model_id: str):
    """Get metadata for a specific model."""
    try:
        return mcp_service.get_model_metadata(model_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict", response_model=ModelResponse)
async def predict(request: ModelRequest):
    """Make a prediction using the Model Context Protocol."""
    try:
        return mcp_service.predict(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))