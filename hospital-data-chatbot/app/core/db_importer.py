# app/core/db_importer.py
from app.utils.db import get_db_connection, create_tables, insert_patient_data, insert_metadata

class DbImporter:
    """Handles importing data to Aurora PostgreSQL."""
    
    def __init__(self):
        self.conn = get_db_connection()
        
    def setup_database(self):
        """Set up database tables."""
        create_tables(self.conn)
    
    def import_data(self, patient_data, metadata):
        """Import both patient data and metadata into the database."""
        # Create tables if they don't exist
        self.setup_database()
        
        # Import data
        patient_count = insert_patient_data(self.conn, patient_data)
        metadata_count = insert_metadata(self.conn, metadata)
        
        return {
            'patient_records': patient_count,
            'metadata_records': metadata_count
        }
        
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()