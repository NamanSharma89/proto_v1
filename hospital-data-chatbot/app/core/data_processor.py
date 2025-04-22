import polars as pl
import re
import os
from app.utils.aws import upload_to_s3
from app.config.settings import AppConfig

class DataProcessor:
    """Handles loading and processing of hospital data."""
    
    def __init__(self):
        self.patient_data = None
        self.diagnosis_data = None
        self.load_data()
    
    def load_data(self):
        """Load hospital data from source."""
        data_path = os.path.join(AppConfig.DATA_DIR, 'raw', 'hospital_data.xlsx')
        
        # Load patient data from "Patient Details" tab
        self.patient_data = pl.read_excel(data_path, sheet_name="Patient Details")
        self.patient_data = self._convert_column_names_to_snake_case(self.patient_data)
        
        # Load diagnosis data from "Diagnosis Details" tab
        self.diagnosis_data = pl.read_excel(data_path, sheet_name="Diagnosis Details")
        self.diagnosis_data = self._convert_column_names_to_snake_case(self.diagnosis_data)
        
        # Preprocess both datasets
        self._preprocess_patient_data()
        self._preprocess_diagnosis_data()
    
    def _convert_column_names_to_snake_case(self, df):
        """Convert column names to snake_case."""
        # Create a mapping of original names to snake_case names
        column_mapping = {
            col: re.sub(r'(?<!^)(?=[A-Z])', '_', col).lower().replace(' ', '_').replace('-', '_')
            for col in df.columns
        }
        
        # Rename columns
        return df.rename(column_mapping)
    
    def _preprocess_patient_data(self):
        """Clean and preprocess the patient data."""
        # Handle missing values
        self.patient_data = self.patient_data.fill_null(0)
        
        # Convert date columns if they exist
        date_columns = ['admission_date', 'discharge_date']
        for col in date_columns:
            if col in self.patient_data.columns:
                self.patient_data = self.patient_data.with_columns(
                    pl.col(col).str.to_datetime()
                )
        
        # Calculate stay duration if admission and discharge dates exist
        if 'admission_date' in self.patient_data.columns and 'discharge_date' in self.patient_data.columns:
            self.patient_data = self.patient_data.with_columns(
                (pl.col('discharge_date') - pl.col('admission_date')).dt.total_days().alias('stay_duration')
            )
    
    def _preprocess_diagnosis_data(self):
        """Clean and preprocess the diagnosis data."""
        # Handle missing values
        self.diagnosis_data = self.diagnosis_data.fill_null(0)
        
        # Ensure registry_id is a string for joining
        if 'registry_id' in self.diagnosis_data.columns:
            self.diagnosis_data = self.diagnosis_data.with_columns(
                pl.col('registry_id').cast(pl.Utf8)
            )
    
    def save_processed_data(self):
        """Save processed data to files or S3."""
        if AppConfig.USE_S3:
            # Save both dataframes
            patient_data_path = upload_to_s3(
                self.patient_data.to_pandas() if hasattr(self.patient_data, 'to_pandas') else self.patient_data,
                AppConfig.S3_BUCKET,
                'processed/patient_data.csv'
            )
            
            diagnosis_data_path = upload_to_s3(
                self.diagnosis_data.to_pandas() if hasattr(self.diagnosis_data, 'to_pandas') else self.diagnosis_data,
                AppConfig.S3_BUCKET,
                'processed/diagnosis_data.csv'
            )
            
            return {
                'patient_data': patient_data_path,
                'diagnosis_data': diagnosis_data_path
            }
        else:
            # Save to local CSV files
            patient_data_path = os.path.join(AppConfig.DATA_DIR, 'processed', 'patient_data.csv')
            diagnosis_data_path = os.path.join(AppConfig.DATA_DIR, 'processed', 'diagnosis_data.csv')
            
            self.patient_data.write_csv(patient_data_path)
            self.diagnosis_data.write_csv(diagnosis_data_path)
            
            return {
                'patient_data': patient_data_path,
                'diagnosis_data': diagnosis_data_path
            }
    
    def get_data_stats(self):
        """Get basic statistics about both datasets."""
        stats = {
            "patient_data": {
                "record_count": self.patient_data.height,
                "column_count": self.patient_data.width,
                "columns": self.patient_data.columns
            },
            "diagnosis_data": {
                "record_count": self.diagnosis_data.height,
                "column_count": self.diagnosis_data.width,
                "columns": self.diagnosis_data.columns
            }
        }
        return stats