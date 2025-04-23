import os
import re
import polars as pl
from pathlib import Path
from datetime import datetime
import concurrent.futures
from typing import Dict, Tuple, Optional, List, Any

from app.utils.aws import upload_to_s3
from app.utils.db import get_db_connection, create_tables, insert_data
from app.config.settings import AppConfig
from app.utils.logging import get_logger


class DataProcessor:
    """
    Enhanced data processor that handles loading, processing, and storing hospital data.
    Features:
    - Robust data loading from Excel with better error handling
    - Efficient data type conversion and schema management
    - Parallel processing capabilities
    - Direct database ingestion
    - Data validation and cleaning
    """

    logger = get_logger(__name__)
    
    def __init__(self, auto_load: bool = True, auto_ingest_db: bool = True):
        """
        Initialize the data processor.
        
        Args:
            auto_load: Automatically load data during initialization
            auto_ingest_db: Automatically ingest data into database after loading
        """
        self.patient_data = None
        self.diagnosis_data = None
        self.data_path = Path(AppConfig.DATA_DIR) / 'raw' / 'hospital_data.xlsx'
        
        # Track data stats for monitoring
        self.stats = {
            "patient_records": 0,
            "diagnosis_records": 0,
            "load_timestamp": None,
            "processing_time_sec": 0,
            "data_quality": {},
        }
        
        if auto_load:
            self.load_data()
            
        if auto_ingest_db and self.patient_data is not None and self.diagnosis_data is not None:
            self.ingest_to_database()
    
    def load_data(self) -> Tuple[pl.DataFrame, pl.DataFrame]:
        """
        Load hospital data from source Excel file with improved error handling.
        
        Returns:
            Tuple containing (patient_data, diagnosis_data)
        """
        start_time = datetime.now()
        
        if not os.path.exists(self.data_path):
            self.logger.error(f"Data file not found: {self.data_path}")
            raise FileNotFoundError(f"Hospital data file not found at {self.data_path}")
        
        self.logger.info(f"Loading data from {self.data_path}")
        
        try:
            # Load data using a context manager to ensure proper resource cleanup
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Load both sheets concurrently for better performance
                patient_future = executor.submit(self._load_patient_data)
                diagnosis_future = executor.submit(self._load_diagnosis_data)
                
                # Get results
                self.patient_data = patient_future.result()
                self.diagnosis_data = diagnosis_future.result()

            # Track stats
            self.stats["patient_records"] = self.patient_data.height
            self.stats["diagnosis_records"] = self.diagnosis_data.height
            self.stats["load_timestamp"] = datetime.now()
            self.stats["processing_time_sec"] = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"Successfully loaded {self.patient_data.height} patient records and "
                            f"{self.diagnosis_data.height} diagnosis records")
            
            # Run data quality checks
            self._validate_data_integrity()
            
            return self.patient_data, self.diagnosis_data
            
        except Exception as e:
            self.logger.error(f"Failed to load data: {str(e)}", exc_info=True)
            raise
    
    def _load_patient_data(self) -> pl.DataFrame:
        """
        Load patient data from Excel with enhanced processing.
        
        Returns:
            Processed patient data as a Polars DataFrame
        """
        try:
            # Load raw data directly with read_excel
            df = pl.read_excel(self.data_path, sheet_name="Patient Details")
            
            # Convert column names to snake_case
            df = self._convert_column_names_to_snake_case(df)
            
            # Handle schema with explicit data types for important columns
            schema = {
                "age": pl.Int32,
                "registry_id": pl.Utf8,
                "gender": pl.Utf8,
                "admission_date": pl.Utf8,
                "discharge_date": pl.Utf8,
            }
            
            # Apply schema with error handling for each column
            for col, dtype in schema.items():
                if col in df.columns:
                    try:
                        df = df.with_columns(
                            pl.col(col).cast(dtype, strict=False)
                        )
                    except Exception as e:
                        self.logger.warning(f"Could not convert column {col} to {dtype}: {str(e)}")
                        # Keep as string if conversion fails
                        df = df.with_columns(pl.col(col).cast(pl.Utf8, strict=False))
            
            # Process and enhance the data
            df = self._preprocess_patient_data(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading patient data: {str(e)}", exc_info=True)
            raise
    
    def _load_diagnosis_data(self) -> pl.DataFrame:
        """
        Load diagnosis data from Excel with enhanced processing.
        
        Returns:
            Processed diagnosis data as a Polars DataFrame
        """
        try:
            # Load raw data directly with read_excel
            df = pl.read_excel(self.data_path, sheet_name="Diagnosis Details")
            
            # Convert column names to snake_case
            df = self._convert_column_names_to_snake_case(df)
            
            # Set schema with appropriate types
            schema = {
                "registry_id": pl.Utf8,
                "diagnosis": pl.Utf8,
                "diagnosis_date": pl.Utf8,
                "diagnosis_code": pl.Utf8,
            }
            
            # Apply schema with error handling
            for col, dtype in schema.items():
                if col in df.columns:
                    try:
                        df = df.with_columns(
                            pl.col(col).cast(dtype, strict=False)
                        )
                    except Exception as e:
                        self.logger.warning(f"Could not convert column {col} to {dtype}: {str(e)}")
                        df = df.with_columns(pl.col(col).cast(pl.Utf8, strict=False))
            
            # Process the data
            df = self._preprocess_diagnosis_data(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading diagnosis data: {str(e)}", exc_info=True)
            raise
    
    def _convert_column_names_to_snake_case(self, df: pl.DataFrame) -> pl.DataFrame:
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
    
    def _preprocess_patient_data(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Clean and preprocess the patient data with enhanced features.
        
        Args:
            df: Raw patient data DataFrame
            
        Returns:
            Processed patient DataFrame
        """
        # Handle missing values - fill nulls with appropriate values by type
        df = df.fill_null(strategy="zero")  # Use zero for numeric columns
        df = df.with_columns([
            # Fill string columns with empty string
            pl.col(pl.Utf8).fill_null("")
        ])
        
        # Convert date columns if they exist
        date_columns = ['admission_date', 'discharge_date']
        for col in date_columns:
            if col in df.columns:
                try:
                    # Try multiple date formats to handle various input formats
                    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%d/%m/%Y"]:
                        try:
                            df = df.with_columns(
                                pl.col(col).str.strptime(pl.Datetime, fmt=fmt, strict=False)
                                .alias(f"{col}_dt")
                            )
                            self.logger.info(f"Successfully converted {col} using format {fmt}")
                            break  # Stop trying formats if one succeeds
                        except:
                            continue
                    
                    # If no format worked, log a warning
                    if f"{col}_dt" not in df.columns:
                        self.logger.warning(f"Could not parse date column {col} with any standard format")
                        
                    # Calculate stay duration if both dates are available
                    if all(f"{c}_dt" in df.columns for c in date_columns):
                        df = df.with_columns(
                            (pl.col('discharge_date_dt') - pl.col('admission_date_dt'))
                            .dt.total_days()
                            .alias('stay_duration')
                        )
                        
                        # Ensure stay duration is not negative (data quality check)
                        df = df.with_columns(
                            pl.when(pl.col('stay_duration') < 0)
                            .then(None)  # Replace negative durations with NULL
                            .otherwise(pl.col('stay_duration'))
                            .alias('stay_duration')
                        )
                        
                except Exception as e:
                    self.logger.warning(f"Error processing date columns: {str(e)}")
        
        # Additional preprocessing steps
        if 'age' in df.columns:
            # Handle age outliers
            df = df.with_columns(
                pl.when((pl.col('age') < 0) | (pl.col('age') > 120))
                .then(None)  # Replace implausible ages with NULL
                .otherwise(pl.col('age'))
                .alias('age')
            )
        
        # Add age groups for easier analysis if age column exists
        if 'age' in df.columns:
            df = df.with_columns(
                pl.when(pl.col('age') < 18).then('pediatric')
                .when(pl.col('age') < 65).then('adult')
                .when(pl.col('age') >= 65).then('elderly')
                .otherwise('unknown')
                .alias('age_group')
            )
        
        return df
    
    def _preprocess_diagnosis_data(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Clean and preprocess the diagnosis data with enhanced features.
        
        Args:
            df: Raw diagnosis data DataFrame
            
        Returns:
            Processed diagnosis DataFrame
        """
        # Handle missing values
        df = df.fill_null("")
        
        # Process diagnosis codes for consistency
        if 'diagnosis_code' in df.columns:
            # Strip whitespace and sanitize codes
            df = df.with_columns(
                pl.col('diagnosis_code').str.strip().str.to_uppercase()
            )
        
        # Process diagnosis date if it exists
        if 'diagnosis_date' in df.columns:
            try:
                # Try multiple date formats
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%d/%m/%Y"]:
                    try:
                        df = df.with_columns(
                            pl.col('diagnosis_date').str.strptime(pl.Datetime, fmt=fmt, strict=False)
                            .alias('diagnosis_date_dt')
                        )
                        break  # Stop if successful
                    except:
                        continue
            except Exception as e:
                self.logger.warning(f"Could not convert diagnosis_date to datetime: {str(e)}")
        
        # Check if registry_id is in both dataframes
        if 'registry_id' not in df.columns:
            self.logger.warning("registry_id column missing in diagnosis data, critical for relational integrity")
        
        return df
    
    def _validate_data_integrity(self) -> Dict[str, Any]:
        """
        Perform data validation checks to ensure data integrity.
        
        Returns:
            Dictionary with validation results
        """
        validation_results = {}
        
        if self.patient_data is None or self.diagnosis_data is None:
            self.logger.error("Cannot validate data integrity - data not loaded")
            return {"error": "Data not loaded"}
        
        # Check for patients without registry_id
        if 'registry_id' in self.patient_data.columns:
            missing_ids = self.patient_data.filter(
                pl.col('registry_id').is_null() | (pl.col('registry_id') == "")
            ).height
            
            validation_results['missing_patient_ids'] = missing_ids
            if missing_ids > 0:
                self.logger.warning(f"Found {missing_ids} patients without registry_id")
        
        # Check for orphaned diagnoses (no matching patient)
        if ('registry_id' in self.patient_data.columns and 
            'registry_id' in self.diagnosis_data.columns):
            
            # Get all patient IDs
            patient_ids = set(self.patient_data.select('registry_id').to_series().to_list())
            
            # Check which diagnosis records don't have a matching patient
            orphaned_diagnoses = self.diagnosis_data.filter(
                ~pl.col('registry_id').is_in(patient_ids)
            ).height
            
            validation_results['orphaned_diagnoses'] = orphaned_diagnoses
            if orphaned_diagnoses > 0:
                self.logger.warning(f"Found {orphaned_diagnoses} diagnoses without a matching patient")
        
        # Check for duplicate registry_ids in patient data
        if 'registry_id' in self.patient_data.columns:
            duplicate_ids = (
                self.patient_data.group_by('registry_id')
                .agg(pl.count().alias('count'))
                .filter(pl.col('count') > 1)
                .height
            )
            
            validation_results['duplicate_patient_ids'] = duplicate_ids
            if duplicate_ids > 0:
                self.logger.warning(f"Found {duplicate_ids} duplicate patient registry_ids")
        
        # Update stats with validation results
        self.stats['data_quality'] = validation_results
        
        return validation_results
    
    def ingest_to_database(self) -> Dict[str, Any]:
        """
        Ingest processed data into the database.
        
        Returns:
            Dictionary with ingestion results
        """
        if self.patient_data is None or self.diagnosis_data is None:
            raise ValueError("No data available for ingestion - load data first")
        
        try:
            self.logger.info("Starting database ingestion process")
            self.logger.debug(f"Connection details: host={AppConfig.DB_HOST}, port={AppConfig.DB_PORT}, db={AppConfig.DB_NAME}")
            
            # Log data shape before ingestion
            self.logger.debug(f"Patient data shape: {self.patient_data.shape}, columns: {self.patient_data.columns}")
            self.logger.debug(f"Diagnosis data shape: {self.diagnosis_data.shape}, columns: {self.diagnosis_data.columns}")
            
            conn = get_db_connection()
            
            try:
                # Create database tables if they don't exist
                self.logger.info("Creating database tables if they don't exist")
                create_tables(conn, self.patient_data, self.diagnosis_data)
                
                # Insert patient data first (for referential integrity)
                self.logger.info(f"Inserting {self.patient_data.height} patient records")
                patient_count = insert_data(conn, "patient_details", self.patient_data)
                
                # Insert diagnosis data linked to patients
                self.logger.info(f"Inserting {self.diagnosis_data.height} diagnosis records")
                diagnosis_count = insert_data(conn, "diagnosis_details", self.diagnosis_data)
                
                # Commit transaction
                conn.commit()
                self.logger.info("Transaction committed successfully")
                
                # Return insertion results
                result = {
                    "status": "success",
                    "patient_records_inserted": patient_count,
                    "diagnosis_records_inserted": diagnosis_count,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Update stats
                self.stats["db_ingestion"] = result
                
                self.logger.info(f"Database ingestion complete: {patient_count} patients, {diagnosis_count} diagnoses")
                return result
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"Database ingestion failed: {str(e)}", exc_info=True)
                raise
            finally:
                conn.close()
                self.logger.debug("Database connection closed")
                
        except Exception as e:
            error_msg = f"Failed to ingest data to database: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "status": "error",
                "message": error_msg,
                "timestamp": datetime.now().isoformat()
            }
    
    def save_processed_data(self) -> Dict[str, str]:
        """
        Save processed data to files or S3.
        
        Returns:
            Dictionary with file paths
        """
        if self.patient_data is None or self.diagnosis_data is None:
            raise ValueError("No processed data available to save")
        
        try:
            # Create directories if they don't exist
            if not AppConfig.USE_S3:
                os.makedirs(os.path.join(AppConfig.DATA_DIR, 'processed'), exist_ok=True)
            
            if AppConfig.USE_S3:
                # Save both dataframes to S3
                self.logger.info(f"Saving processed data to S3 bucket {AppConfig.S3_BUCKET}")
                
                patient_data_path = upload_to_s3(
                    self.patient_data,
                    AppConfig.S3_BUCKET,
                    'processed/patient_data.csv'
                )
                
                diagnosis_data_path = upload_to_s3(
                    self.diagnosis_data,
                    AppConfig.S3_BUCKET,
                    'processed/diagnosis_data.csv'
                )
            else:
                # Save to local CSV files
                patient_data_path = os.path.join(AppConfig.DATA_DIR, 'processed', 'patient_data.csv')
                diagnosis_data_path = os.path.join(AppConfig.DATA_DIR, 'processed', 'diagnosis_data.csv')
                
                self.logger.info(f"Saving processed data to local files: {patient_data_path}, {diagnosis_data_path}")
                
                self.patient_data.write_csv(patient_data_path)
                self.diagnosis_data.write_csv(diagnosis_data_path)
            
            self.logger.info("Data saved successfully")
            
            return {
                'patient_data': patient_data_path,
                'diagnosis_data': diagnosis_data_path
            }
        except Exception as e:
            self.logger.error(f"Failed to save processed data: {str(e)}", exc_info=True)
            raise
    
    def get_data_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the loaded datasets.
        
        Returns:
            Dictionary with dataset statistics
        """
        if self.patient_data is None or self.diagnosis_data is None:
            return {"error": "No data loaded"}
        
        try:
            # Generate descriptive statistics for patient data
            patient_stats = {
                "record_count": self.patient_data.height,
                "column_count": self.patient_data.width,
                "columns": self.patient_data.columns,
            }
            
            # Add more detailed statistics for numeric columns
            if 'age' in self.patient_data.columns:
                try:
                    age_stats = self.patient_data.select([
                        pl.col('age').mean().alias('avg_age'),
                        pl.col('age').min().alias('min_age'),
                        pl.col('age').max().alias('max_age'),
                        pl.col('age').median().alias('median_age')
                    ]).to_dicts()[0]
                    patient_stats['age_stats'] = age_stats
                except:
                    pass
            
            if 'stay_duration' in self.patient_data.columns:
                try:
                    stay_stats = self.patient_data.select([
                        pl.col('stay_duration').mean().alias('avg_stay'),
                        pl.col('stay_duration').min().alias('min_stay'),
                        pl.col('stay_duration').max().alias('max_stay'),
                        pl.col('stay_duration').median().alias('median_stay')
                    ]).to_dicts()[0]
                    patient_stats['stay_stats'] = stay_stats
                except:
                    pass
            
            # Gender distribution if available
            if 'gender' in self.patient_data.columns:
                try:
                    gender_counts = (
                        self.patient_data
                        .group_by('gender')
                        .agg(pl.count().alias('count'))
                        .sort('count', descending=True)
                        .to_dicts()
                    )
                    patient_stats['gender_distribution'] = gender_counts
                except:
                    pass
            
            # Diagnosis data statistics
            diagnosis_stats = {
                "record_count": self.diagnosis_data.height,
                "column_count": self.diagnosis_data.width,
                "columns": self.diagnosis_data.columns,
            }
            
            # Top diagnoses if available
            if 'diagnosis' in self.diagnosis_data.columns:
                try:
                    top_diagnoses = (
                        self.diagnosis_data
                        .group_by('diagnosis')
                        .agg(pl.count().alias('count'))
                        .sort('count', descending=True)
                        .head(10)
                        .to_dicts()
                    )
                    diagnosis_stats['top_diagnoses'] = top_diagnoses
                except:
                    pass
            
            # Diagnoses per patient
            if 'registry_id' in self.diagnosis_data.columns:
                try:
                    diagnoses_per_patient = (
                        self.diagnosis_data
                        .group_by('registry_id')
                        .agg(pl.count().alias('diagnosis_count'))
                    )
                    
                    diag_stats = diagnoses_per_patient.select([
                        pl.col('diagnosis_count').mean().alias('avg_diagnoses_per_patient'),
                        pl.col('diagnosis_count').min().alias('min_diagnoses_per_patient'),
                        pl.col('diagnosis_count').max().alias('max_diagnoses_per_patient'),
                        pl.col('diagnosis_count').median().alias('median_diagnoses_per_patient')
                    ]).to_dicts()[0]
                    
                    diagnosis_stats['diagnoses_per_patient'] = diag_stats
                except:
                    pass
            
            # Combined stats
            stats = {
                "patient_data": patient_stats,
                "diagnosis_data": diagnosis_stats,
                "processing_stats": {
                    "load_timestamp": self.stats.get("load_timestamp"),
                    "processing_time_sec": self.stats.get("processing_time_sec"),
                },
                "data_quality": self.stats.get("data_quality", {})
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error generating data statistics: {str(e)}", exc_info=True)
            return {
                "error": f"Failed to generate statistics: {str(e)}",
                "patient_record_count": self.patient_data.height if self.patient_data is not None else 0,
                "diagnosis_record_count": self.diagnosis_data.height if self.diagnosis_data is not None else 0
            }