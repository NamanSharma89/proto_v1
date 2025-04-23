import polars as pl
import re
import os
from app.utils.aws import upload_to_s3
from app.config.settings import AppConfig
from app.utils.logging import setup_logging
from app.utils.logging import get_logger

class DataProcessor:
    """Handles loading and processing of hospital data."""



    logger = get_logger(__name__)
    
    def __init__(self):
        self.patient_data = None
        self.diagnosis_data = None
        self.load_data()
    
    def load_data(self):
        """Load hospital data from source."""
        data_path = os.path.join(AppConfig.DATA_DIR, 'raw', 'hospital_data.xlsx')
        
        # Load patient data from "Patient Details" tab
        try:
            self.logger.info(f"Loading patient data from {data_path}, sheet 'Patient Details'")
            # First load the data normally
            self.patient_data = pl.read_excel(data_path, sheet_name="Patient Details")
            
            # Then convert all columns to strings
            for col in self.patient_data.columns:
                self.patient_data = self.patient_data.with_columns(
                    pl.col(col).cast(pl.Utf8)
                )
            
            self.patient_data = self._convert_column_names_to_snake_case(self.patient_data)
            self.logger.info(f"Successfully loaded patient data: {self.patient_data.shape}")
        except Exception as e:
            self.logger.error(f"Error loading patient data: {str(e)}")
            raise
        
        # Load diagnosis data from "Diagnosis Details" tab
        try:
            self.logger.info(f"Loading diagnosis data from {data_path}, sheet 'Diagnosis Details'")
            # First load the data normally
            self.diagnosis_data = pl.read_excel(data_path, sheet_name="Diagnosis Details")
            
            # Then convert all columns to strings
            for col in self.diagnosis_data.columns:
                self.diagnosis_data = self.diagnosis_data.with_columns(
                    pl.col(col).cast(pl.Utf8)
                )
            
            self.diagnosis_data = self._convert_column_names_to_snake_case(self.diagnosis_data)
            self.logger.info(f"Successfully loaded diagnosis data: {self.diagnosis_data.shape}")
        except Exception as e:
            self.logger.error(f"Error loading diagnosis data: {str(e)}")
            raise
        
        # Preprocess both datasets
        self._preprocess_patient_data()
        self._preprocess_diagnosis_data()

        # Log the number of records loaded
        self.logger.info(f"Loaded {self.patient_data.height} records from Patient Details")
        self.logger.info(f"Loaded {self.diagnosis_data.height} records from Diagnosis Details")
        # Log the column names
        self.logger.info(f"Patient Details columns: {self.patient_data.columns}")
        self.logger.info(f"Diagnosis Details columns: {self.diagnosis_data.columns}")    
    

    def _convert_column_names_to_snake_case(self, df):
        """
        Convert column names to snake_case and validate no duplicates are created.
        
        Args:
            df: Polars DataFrame with original column names
            
        Returns:
            DataFrame with snake_case column names
        """
        # Create a mapping of original names to snake_case names
        column_mapping = {}
        
        for col in df.columns:
            # Clean the column name to keep only alphanumeric characters and spaces
            clean_col = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in col)
            
            # Convert spaces, hyphens and camelCase to snake_case
            # 1. Replace spaces and hyphens with underscores
            snake_col = clean_col.replace(' ', '_').replace('-', '_')
            
            # 2. Handle camelCase by inserting underscore before capital letters
            snake_col = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', snake_col)
            
            # 3. Convert to lowercase and remove any double underscores
            snake_col = snake_col.lower().replace('__', '_').strip('_')
            
            column_mapping[col] = snake_col
        
        # Check for duplicate column names after conversion
        snake_case_names = list(column_mapping.values())
        duplicate_names = set([name for name in snake_case_names if snake_case_names.count(name) > 1])
        
        # If duplicates found, modify the column names to make them unique
        if duplicate_names:
            self.logger.warning(f"Found duplicate column names after snake_case conversion: {duplicate_names}")
            
            # Track columns that have been processed to handle duplicates
            processed_names = {}
            
            # Update mapping to make duplicate column names unique
            for original_col, snake_col in list(column_mapping.items()):
                if snake_col in duplicate_names:
                    # If this name was already processed, add a numeric suffix
                    if snake_col in processed_names:
                        processed_names[snake_col] += 1
                        unique_name = f"{snake_col}_{processed_names[snake_col]}"
                        column_mapping[original_col] = unique_name
                        self.logger.info(f"Renamed duplicate column '{original_col}' to '{unique_name}'")
                    else:
                        # First occurrence of this duplicate name
                        processed_names[snake_col] = 1
        
        # Validate final mapping has no duplicates
        if len(set(column_mapping.values())) != len(column_mapping):
            remaining_duplicates = [name for name, count in 
                                {name: list(column_mapping.values()).count(name) for name in set(column_mapping.values())}.items() 
                                if count > 1]
            raise ValueError(f"Failed to resolve duplicate column names: {remaining_duplicates}. Review your data schema.")
        
        # Log the column name mapping for reference
        for original, converted in column_mapping.items():
            if original != converted:
                self.logger.debug(f"Column renamed: '{original}' -> '{converted}'")
        
        # Rename columns
        return df.rename(column_mapping)
    
    def _preprocess_patient_data(self):
        """Clean and preprocess the patient data."""
        # Handle missing values - keep strings as empty strings
        self.patient_data = self.patient_data.fill_null("")
        
        # Safely attempt to convert date columns if they exist
        date_columns = ['admission_date', 'discharge_date']
        for col in date_columns:
            if col in self.patient_data.columns:
                try:
                    # Try to convert to datetime, but keep as string if it fails
                    self.patient_data = self.patient_data.with_columns(
                        pl.col(col).str.strptime(pl.Datetime, fmt="%Y-%m-%d", strict=False).alias(f"{col}_dt")
                    )
                    # If successful, calculate stay duration
                    if f"{col}_dt" in self.patient_data.columns and col == 'admission_date' and 'discharge_date_dt' in self.patient_data.columns:
                        try:
                            self.patient_data = self.patient_data.with_columns(
                                (pl.col('discharge_date_dt') - pl.col('admission_date_dt')).dt.total_days().alias('stay_duration')
                            )
                        except Exception as e:
                            self.logger.warning(f"Could not calculate stay duration: {str(e)}")
                except Exception as e:
                    self.logger.warning(f"Could not convert {col} to datetime: {str(e)}")

    def _preprocess_diagnosis_data(self):
        """Clean and preprocess the diagnosis data."""
        # Handle missing values - keep strings as empty strings
        self.diagnosis_data = self.diagnosis_data.fill_null("")
        
        # No type conversions for now - keep everything as strings
        pass
    
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