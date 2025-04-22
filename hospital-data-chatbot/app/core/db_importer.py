# app/core/db_importer.py
from app.utils.db import get_db_connection, create_tables, insert_data

class DbImporter:
    """Handles importing data to Aurora PostgreSQL."""
    
    def __init__(self):
        self.conn = get_db_connection()
        
    def setup_database(self, patient_data, diagnosis_data):
        """Set up database tables with proper relationships."""
        create_tables(self.conn, patient_data, diagnosis_data)
    
    def import_data(self, patient_data, diagnosis_data):
        """Import both patient and diagnosis data into the database."""
        # Create tables if they don't exist
        self.setup_database(patient_data, diagnosis_data)
        
        # Import data
        patient_count = insert_data(self.conn, "patient_details", patient_data)
        diagnosis_count = insert_data(self.conn, "diagnosis_details", diagnosis_data)
        
        return {
            'patient_records': patient_count,
            'diagnosis_records': diagnosis_count
        }
        
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()