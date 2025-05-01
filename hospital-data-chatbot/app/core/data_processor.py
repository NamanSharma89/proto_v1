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
    
    def __init__(self, auto_load: bool = True, auto_ingest_db: bool = False, recreate_db_schema: bool = False):
        """
        Initialize the data processor.
        
        Args:
            auto_load: Automatically load data during initialization
            auto_ingest_db: Automatically ingest data into database after loading
            recreate_db_schema: Drop and recreate database schema (development mode only)
        """
        self.patient_data = None
        self.diagnosis_data = None
        self.data_path = Path(AppConfig.DATA_DIR) / 'raw' / 'hospital_data.xlsx'
        self.recreate_db_schema = recreate_db_schema
        
        # Safety check - only allow schema recreation in development environments
        if self.recreate_db_schema and not AppConfig.is_development():
            self.logger.warning("Schema recreation requested but not allowed in non-development environment")
            self.recreate_db_schema = False
            
        if self.recreate_db_schema:
            self.logger.warning("Database schema will be dropped and recreated! Use this only in development.")
        
        # Track data stats for monitoring
        self.stats = {
            "patient_records": 0,
            "diagnosis_records": 0,
            "load_timestamp": None,
            "processing_time_sec": 0,
            "data_quality": {},
            "environment": AppConfig.get_environment_name(),
        }
        
        self.logger.info(f"DataProcessor initialized in {AppConfig.get_environment_name()} environment")
        
        # In production, always load but don't auto-ingest to allow validation
        if AppConfig.is_production():
            self.logger.info("Production environment detected: Auto-ingest disabled for safety")
            auto_ingest_db = False
            self.recreate_db_schema = False
        
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
        Load patient data from Excel without schema modifications.
        
        Returns:
            Patient data as a Polars DataFrame with standardized column names
        """
        try:
            # Load raw data directly with read_excel
            self.logger.info(f"Loading patient data from {self.data_path}, sheet 'Patient Details'")
            df = pl.read_excel(self.data_path, sheet_name="Patient Details")
            
            # Convert column names to snake_case
            df = self._convert_column_names_to_snake_case(df)
            self.logger.debug(f"Loaded patient data with {df.height} rows and {df.width} columns")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading patient data: {str(e)}", exc_info=True)
            raise

    def _load_diagnosis_data(self) -> pl.DataFrame:
        """
        Load diagnosis data from Excel without schema modifications.
        
        Returns:
            Diagnosis data as a Polars DataFrame with standardized column names
        """
        try:
            # Load raw data directly with read_excel
            self.logger.info(f"Loading diagnosis data from {self.data_path}, sheet 'Diagnosis Details'")
            df = pl.read_excel(self.data_path, sheet_name="Diagnosis Details")
            
            # Convert column names to snake_case
            df = self._convert_column_names_to_snake_case(df)
            self.logger.debug(f"Loaded diagnosis data with {df.height} rows and {df.width} columns")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading diagnosis data: {str(e)}", exc_info=True)
            raise
    
    def _convert_column_names_to_snake_case(self, df):
        """
        Convert column names to snake_case and validate no duplicates are created.
        Handles decimal numbers in column names and removes leading numbers.
        
        Args:
            df: Polars DataFrame with original column names
            
        Returns:
            DataFrame with sanitized snake_case column names
        """
        # Create a mapping of original names to snake_case names
        column_mapping = {}
        
        for col in df.columns:
            # Clean the column name to keep only alphanumeric characters, spaces, and periods
            clean_col = ''.join(c if c.isalnum() or c.isspace() or c == '.' else ' ' for c in col)
            
            # 1. Replace spaces and hyphens with underscores
            snake_col = clean_col.replace(' ', '_').replace('-', '_')
            
            # 2. Handle camelCase by inserting underscore before capital letters
            snake_col = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', snake_col)
            
            # 3. Convert to lowercase and remove any double underscores
            snake_col = snake_col.lower().replace('__', '_').strip('_')
            
            # 4. Remove decimal number prefixes with any number of decimal points 
            # (e.g., "5.1.2_retriage" -> "retriage", "5.1_retriage" -> "retriage")
            # This pattern removes floating point numbers at the beginning of column names
            snake_col = re.sub(r'^(\d+(\.\d+)+)[\._]*', '', snake_col)
            
            # 5. Remove any remaining leading digits (e.g. "1_hospital_id" -> "hospital_id")
            snake_col = re.sub(r'^[0-9]+[\._]*', '', snake_col)
            
            # 6. If removing digits results in an empty string or just underscores, use "column_X"
            if not snake_col or snake_col.strip('_') == '':
                snake_col = f"column_{df.columns.index(col)}"
            
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
    
    def _preprocess_patient_data(self, df):
        """
        Minimal preprocessing for patient data, keeping data as-is.
        
        Args:
            df: Patient data DataFrame
                
        Returns:
            Original DataFrame with minimal changes
        """
        # Handle null values if needed - can be removed if you want to keep nulls as is
        df = df.fill_null(None)
        
        self.logger.info("Minimal patient data preprocessing complete - keeping data as-is")
        
        return df

    def _preprocess_diagnosis_data(self, df):
        """
        Minimal preprocessing for diagnosis data, keeping data as-is.
        
        Args:
            df: Diagnosis data DataFrame
                
        Returns:
            Original DataFrame with minimal changes
        """
        # Handle null values if needed - can be removed if you want to keep nulls as is
        df = df.fill_null(None)
        
        self.logger.info("Minimal diagnosis data preprocessing complete - keeping data as-is")
        
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
        Ingest processed data into the database with enhanced validation.
        
        Returns:
            Dictionary with ingestion results including validation statistics
        """
        if self.patient_data is None or self.diagnosis_data is None:
            raise ValueError("No data available for ingestion - load data first")
        
        try:
            self.logger.info("Starting database ingestion process with validation")
            self.logger.debug(f"Connection details: host={AppConfig.DB_HOST}, port={AppConfig.DB_PORT}, db={AppConfig.DB_NAME}")
            
            # Log data shape before ingestion
            self.logger.debug(f"Patient data shape: {self.patient_data.shape}, columns: {self.patient_data.columns}")
            self.logger.debug(f"Diagnosis data shape: {self.diagnosis_data.shape}, columns: {self.diagnosis_data.columns}")
            
            conn = get_db_connection()
            
            try:
                # Create database tables if they don't exist
                self.logger.info("Creating database tables if they don't exist")
                create_tables(conn, self.patient_data, self.diagnosis_data, drop_if_exists=getattr(self, 'recreate_db_schema', False))
                
                # Insert patient data first (for referential integrity)
                self.logger.info(f"Validating and inserting {self.patient_data.height} patient records")
                patient_stats = insert_data(conn, "patient_details", self.patient_data)
                
                # Insert diagnosis data linked to patients
                self.logger.info(f"Validating and inserting {self.diagnosis_data.height} diagnosis records")
                diagnosis_stats = insert_data(conn, "diagnosis_details", self.diagnosis_data)
                
                # Commit transaction
                conn.commit()
                self.logger.info("Transaction committed successfully")
                
                # Compile and log comprehensive statistics
                success_rate_patients = (patient_stats["valid_records"] / patient_stats["total_records"]) * 100 if patient_stats["total_records"] > 0 else 0
                success_rate_diagnosis = (diagnosis_stats["valid_records"] / diagnosis_stats["total_records"]) * 100 if diagnosis_stats["total_records"] > 0 else 0
                
                self.logger.info(f"Patient data: {patient_stats['valid_records']} inserted, {patient_stats['rejected_records']} rejected ({success_rate_patients:.1f}% success)")
                self.logger.info(f"Diagnosis data: {diagnosis_stats['valid_records']} inserted, {diagnosis_stats['rejected_records']} rejected ({success_rate_diagnosis:.1f}% success)")
                
                # If there were rejected records, log the main reasons
                if patient_stats["rejected_records"] > 0:
                    self.logger.warning("Main reasons for patient data rejection:")
                    for reason, count in sorted(patient_stats.get("error_reasons", {}).items(), key=lambda x: x[1], reverse=True)[:3]:
                        self.logger.warning(f" - {reason}: {count} records")
                
                if diagnosis_stats["rejected_records"] > 0:
                    self.logger.warning("Main reasons for diagnosis data rejection:")
                    for reason, count in sorted(diagnosis_stats.get("error_reasons", {}).items(), key=lambda x: x[1], reverse=True)[:3]:
                        self.logger.warning(f" - {reason}: {count} records")
                
                # Return insertion results
                result = {
                    "status": "success",
                    "patient_records": {
                        "total": patient_stats["total_records"],
                        "inserted": patient_stats["valid_records"],
                        "rejected": patient_stats["rejected_records"],
                        "success_rate": f"{success_rate_patients:.1f}%"
                    },
                    "diagnosis_records": {
                        "total": diagnosis_stats["total_records"],
                        "inserted": diagnosis_stats["valid_records"],
                        "rejected": diagnosis_stats["rejected_records"],
                        "success_rate": f"{success_rate_diagnosis:.1f}%"
                    },
                    "validation_details": {
                        "patient_errors": patient_stats.get("error_reasons", {}),
                        "diagnosis_errors": diagnosis_stats.get("error_reasons", {})
                    },
                    "timestamp": datetime.now().isoformat(),
                    "schema_recreated": getattr(self, 'recreate_db_schema', False)
                }
                
                # Update stats
                self.stats["db_ingestion"] = result
                
                self.logger.info(f"Database ingestion complete with validation")
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