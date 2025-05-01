# app/ml/feature_engineering.py
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import polars as pl
from datetime import datetime, timedelta
from app.utils.db import get_db_connection
from app.utils.logging import get_logger

class FeatureEngineering:
    """Handles feature engineering for machine learning models."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def extract_features(self, feature_set_name: str) -> pl.DataFrame:
        """
        Extract features from PostgreSQL database based on feature set name.
        
        Args:
            feature_set_name: Name of the feature set to extract
            
        Returns:
            Polars DataFrame with extracted features
        """
        if feature_set_name == "patient_risk_factors":
            return self._extract_patient_risk_features()
        elif feature_set_name == "diagnosis_clustering":
            return self._extract_diagnosis_clustering_features()
        elif feature_set_name == "readmission_prediction":
            return self._extract_readmission_features()
        else:
            raise ValueError(f"Unknown feature set: {feature_set_name}")
    
    def _extract_patient_risk_features(self) -> pl.DataFrame:
        """Extract features for patient risk stratification."""
        self.logger.info("Extracting patient risk features")
        
        conn = get_db_connection()
        try:
            # SQL to extract features
            query = """
            SELECT 
                p.registry_id,
                p.age,
                p.gender,
                p.stay_duration,
                COUNT(d.id) AS diagnosis_count,
                AVG(CASE WHEN p.stay_duration IS NOT NULL THEN p.stay_duration ELSE NULL END) 
                    OVER (PARTITION BY 1) AS avg_stay_duration,
                -- Extract chronic condition flags
                MAX(CASE WHEN d.diagnosis ILIKE '%diabetes%' THEN 1 ELSE 0 END) AS has_diabetes,
                MAX(CASE WHEN d.diagnosis ILIKE '%hypertension%' THEN 1 ELSE 0 END) AS has_hypertension,
                MAX(CASE WHEN d.diagnosis ILIKE '%heart%' THEN 1 ELSE 0 END) AS has_heart_condition,
                MAX(CASE WHEN d.diagnosis ILIKE '%kidney%' THEN 1 ELSE 0 END) AS has_kidney_condition,
                MAX(CASE WHEN d.diagnosis ILIKE '%liver%' THEN 1 ELSE 0 END) AS has_liver_condition,
                -- Count previous admissions (if you have that data)
                COUNT(DISTINCT CASE WHEN p.admission_date IS NOT NULL THEN p.admission_date ELSE NULL END) AS admission_count
            FROM 
                patient_details p
            LEFT JOIN 
                diagnosis_details d ON p.registry_id = d.registry_id
            GROUP BY 
                p.registry_id, p.age, p.gender, p.stay_duration
            """
            
            df = pl.read_database(query=query, connection=conn)
            
            # Feature engineering
            df = df.with_columns([
                # Age binning
                pl.when(pl.col("age") < 18).then(0)
                  .when((pl.col("age") >= 18) & (pl.col("age") < 35)).then(1)
                  .when((pl.col("age") >= 35) & (pl.col("age") < 50)).then(2)
                  .when((pl.col("age") >= 50) & (pl.col("age") < 65)).then(3)
                  .when((pl.col("age") >= 65) & (pl.col("age") < 80)).then(4)
                  .otherwise(5)
                  .alias("age_group"),
                
                # Gender encoding
                pl.when(pl.col("gender").is_in(["M", "m", "Male", "male"])).then(1)
                  .when(pl.col("gender").is_in(["F", "f", "Female", "female"])).then(0)
                  .otherwise(None)
                  .alias("gender_encoded"),
                
                # Length of stay compared to average
                (pl.col("stay_duration") / pl.col("avg_stay_duration")).alias("relative_stay_duration"),
                
                # Comorbidity score
                (pl.col("has_diabetes") + pl.col("has_hypertension") + 
                 pl.col("has_heart_condition") + pl.col("has_kidney_condition") + 
                 pl.col("has_liver_condition")).alias("comorbidity_score")
            ])
            
            # Handle missing values
            # For numerical columns, fill with median
            numeric_cols = ["age", "stay_duration", "relative_stay_duration", "comorbidity_score"]
            for col in numeric_cols:
                if col in df.columns:
                    median_val = df[col].median()
                    df = df.with_column(
                        pl.col(col).fill_null(median_val)
                    )
            
            self.logger.info(f"Extracted {df.height} patient risk feature records")
            return df
            
        finally:
            conn.close()
    
    def _extract_diagnosis_clustering_features(self) -> pl.DataFrame:
        """Extract features for diagnosis clustering."""
        self.logger.info("Extracting diagnosis clustering features")
        
        conn = get_db_connection()
        try:
            # SQL to extract diagnosis features
            query = """
            SELECT 
                d.diagnosis,
                AVG(p.age) AS avg_patient_age,
                AVG(p.stay_duration) AS avg_stay_duration,
                COUNT(DISTINCT p.registry_id) AS patient_count,
                SUM(CASE WHEN p.gender IN ('M', 'm', 'Male', 'male') THEN 1 ELSE 0 END) AS male_count,
                SUM(CASE WHEN p.gender IN ('F', 'f', 'Female', 'female') THEN 1 ELSE 0 END) AS female_count
            FROM 
                diagnosis_details d
            JOIN 
                patient_details p ON d.registry_id = p.registry_id
            GROUP BY 
                d.diagnosis
            HAVING
                COUNT(DISTINCT p.registry_id) >= 5  -- Only include diagnoses with at least 5 patients
            """
            
            df = pl.read_database(query=query, connection=conn)
            
            # Feature engineering
            df = df.with_columns([
                # Gender ratio
                (pl.col("male_count") / (pl.col("male_count") + pl.col("female_count"))).alias("male_ratio"),
                
                # Normalize patient count
                (pl.col("patient_count") / pl.col("patient_count").max()).alias("patient_count_normalized")
            ])
            
            # Clean diagnosis text for better clustering
            df = df.with_column(
                pl.col("diagnosis")
                  .str.to_lowercase()
                  .str.replace_all(r'[^\w\s]', '')  # Remove punctuation
                  .str.replace_all(r'\s+', ' ')     # Normalize whitespace
                  .alias("diagnosis_cleaned")
            )
            
            self.logger.info(f"Extracted {df.height} diagnosis clustering feature records")
            return df
            
        finally:
            conn.close()
    
    def _extract_readmission_features(self) -> pl.DataFrame:
        """Extract features for readmission prediction."""
        self.logger.info("Extracting readmission prediction features")
        
        conn = get_db_connection()
        try:
            # This is a more complex query that would require admission/discharge timestamps
            # and a way to identify readmissions in your data
            query = """
            WITH patient_admissions AS (
                SELECT 
                    registry_id,
                    admission_date,
                    discharge_date,
                    LEAD(admission_date) OVER (
                        PARTITION BY registry_id 
                        ORDER BY admission_date
                    ) AS next_admission_date
                FROM 
                    patient_details
                WHERE 
                    admission_date IS NOT NULL
                    AND discharge_date IS NOT NULL
            ),
            readmissions AS (
                SELECT 
                    registry_id,
                    admission_date,
                    discharge_date,
                    next_admission_date,
                    CASE 
                        WHEN next_admission_date IS NOT NULL 
                        AND (next_admission_date - discharge_date) <= INTERVAL '30 days'
                        THEN 1
                        ELSE 0
                    END AS readmitted_30_days
                FROM 
                    patient_admissions
            )
            SELECT 
                p.registry_id,
                p.age,
                p.gender,
                p.stay_duration,
                COUNT(DISTINCT d.diagnosis) AS unique_diagnosis_count,
                r.readmitted_30_days,
                -- Additional features
                EXTRACT(DOW FROM p.admission_date) AS admission_day_of_week,
                EXTRACT(HOUR FROM p.admission_date) AS admission_hour,
                MAX(CASE WHEN d.diagnosis ILIKE '%diabetes%' THEN 1 ELSE 0 END) AS has_diabetes,
                MAX(CASE WHEN d.diagnosis ILIKE '%hypertension%' THEN 1 ELSE 0 END) AS has_hypertension,
                MAX(CASE WHEN d.diagnosis ILIKE '%heart%' THEN 1 ELSE 0 END) AS has_heart_condition
            FROM 
                patient_details p
            JOIN 
                readmissions r ON p.registry_id = r.registry_id AND p.admission_date = r.admission_date
            LEFT JOIN 
                diagnosis_details d ON p.registry_id = d.registry_id
            GROUP BY 
                p.registry_id, p.age, p.gender, p.stay_duration, 
                r.readmitted_30_days, p.admission_date
            """
            
            # Note: This query assumes your schema has admission_date and discharge_date
            # You'll need to adapt it to your actual schema
            
            try:
                df = pl.read_database(query=query, connection=conn)
            except Exception as e:
                self.logger.error(f"Error executing readmission query: {str(e)}")
                # Fall back to a simpler query if the complex one fails
                simple_query = """
                SELECT 
                    p.registry_id,
                    p.age,
                    p.gender,
                    p.stay_duration,
                    COUNT(d.id) AS diagnosis_count
                FROM 
                    patient_details p
                LEFT JOIN 
                    diagnosis_details d ON p.registry_id = d.registry_id
                GROUP BY 
                    p.registry_id, p.age, p.gender, p.stay_duration
                """
                df = pl.read_database(query=simple_query, connection=conn)
                # Add a dummy readmission column since we couldn't calculate it
                df = df.with_column(pl.lit(None).alias("readmitted_30_days"))
            
            # Feature engineering
            df = df.with_columns([
                # Gender encoding
                pl.when(pl.col("gender").is_in(["M", "m", "Male", "male"])).then(1)
                  .when(pl.col("gender").is_in(["F", "f", "Female", "female"])).then(0)
                  .otherwise(None)
                  .alias("gender_encoded")
            ])
            
            self.logger.info(f"Extracted {df.height} readmission feature records")
            return df
            
        finally:
            conn.close()