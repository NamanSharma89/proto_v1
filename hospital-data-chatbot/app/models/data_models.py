# app/models/data_models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Patient(BaseModel):
    """Model representing a patient record."""
    patient_id: str
    age: Optional[int] = None
    gender: Optional[str] = None
    admission_date: Optional[datetime] = None
    discharge_date: Optional[datetime] = None
    diagnosis: Optional[str] = None
    stay_duration: Optional[int] = None
    
    class Config:
        schema_extra = {
            "example": {
                "patient_id": "P12345",
                "age": 45,
                "gender": "F",
                "admission_date": "2023-01-15T10:30:00",
                "discharge_date": "2023-01-20T14:00:00",
                "diagnosis": "Pneumonia",
                "stay_duration": 5
            }
        }

class DataStats(BaseModel):
    """Model representing dataset statistics."""
    record_count: int
    column_count: int
    columns: List[str]