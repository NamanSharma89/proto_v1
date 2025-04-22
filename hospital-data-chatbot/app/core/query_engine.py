# app/core/query_engine.py
import polars as pl
from app.core.llm_connector import BedrockLLM

class QueryEngine:
    """Processes natural language queries on hospital data."""
    
    def __init__(self, patient_data, diagnosis_data):
        self.patient_data = patient_data
        self.diagnosis_data = diagnosis_data
        self.llm = BedrockLLM()
    
    def process_query(self, query):
        """
        Process a user query and always route to the LLM.
        For calculation-related queries, provide context with calculation hints.
        """
        # Prepare context with dataset information
        context = self._prepare_context(query)
        
        # Add calculation capabilities information to the context
        calculation_info = self._get_calculation_capabilities()
        context += calculation_info
        
        # Send to LLM with enhanced context
        llm_response = self.llm.query(query, context)
        
        return llm_response
    
    def _get_calculation_capabilities(self):
        """Provide information about calculation capabilities for the LLM."""
        return """
        CALCULATION CAPABILITIES:
        For any calculations, please use the following format to trigger our calculation API:
        
        [CALCULATE: dataset.operation(column_name)]
        
        Available datasets:
        - patient_details: Contains patient records
        - diagnosis_details: Contains diagnosis information related to patients
        
        Available operations:
        - mean(column_name): Calculate the average of values in the column
        - count(): Count the total number of records
        - min(column_name): Find the minimum value
        - max(column_name): Find the maximum value
        - sum(column_name): Sum all values in the column
        - median(column_name): Find the median value
        - std(column_name): Calculate standard deviation
        - count_unique(column_name): Count unique values
        - count_by_patient(column_name): Count diagnoses grouped by patient
        
        Example usage:
        - To calculate average stay duration: [CALCULATE: patient_details.mean(stay_duration)]
        - To count patients: [CALCULATE: patient_details.count()]
        - To count diagnoses per patient: [CALCULATE: diagnosis_details.count_by_patient(registry_id)]
        
        Please use these calculations when answering queries about statistics or numeric analysis.
        """
    
    def _prepare_context(self, query):
        """Prepare relevant data context based on the query."""
        # Create initial context with data overview
        context = "Hospital Data Overview:\n"
        context += f"1. Patient Details: {self.patient_data.height} patients with {self.patient_data.width} attributes\n"
        context += f"2. Diagnosis Details: {self.diagnosis_data.height} diagnoses with {self.diagnosis_data.width} attributes\n\n"
        
        # Explain the relationship between tables
        context += "Relationship: Each patient (identified by registry_id) can have multiple diagnoses.\n\n"
        
        # Add specific details based on whether the query seems patient-focused or diagnosis-focused
        if any(keyword in query.lower() for keyword in ["patient", "person", "individual", "admission", "discharge"]):
            # Patient-focused query
            context += self._get_patient_context(query)
            context += "\n" + self._get_brief_diagnosis_context()
        elif any(keyword in query.lower() for keyword in ["diagnosis", "condition", "disease", "treatment"]):
            # Diagnosis-focused query
            context += self._get_diagnosis_context(query)
            context += "\n" + self._get_brief_patient_context()
        else:
            # General query - provide both contexts
            context += self._get_patient_context(query, include_sample=True)
            context += "\n" + self._get_diagnosis_context(query, include_sample=True)
        
        return context
    
    def _get_patient_context(self, query, include_sample=True):
        """Get patient data context."""
        context = "PATIENT DETAILS:\n"
        
        # Add column information
        relevant_columns = self._identify_relevant_columns(query, self.patient_data)
        context += "Available patient attributes:\n"
        for col in relevant_columns:
            if col in self.patient_data.columns:
                dtype = self.patient_data.schema[col]
                context += f"- {col} (Type: {dtype})\n"
        
        # Add sample data if requested
        if include_sample:
            sample_size = min(5, self.patient_data.height)
            sample_df = self.patient_data.select(relevant_columns).slice(0, sample_size)
            sample_data = sample_df.to_string()
            context += f"\nSample patient data (first {sample_size} records):\n{sample_data}\n"
        
        return context
    
    def _get_diagnosis_context(self, query, include_sample=True):
        """Get diagnosis data context."""
        context = "DIAGNOSIS DETAILS:\n"
        
        # Add column information
        relevant_columns = self._identify_relevant_columns(query, self.diagnosis_data)
        context += "Available diagnosis attributes:\n"
        for col in relevant_columns:
            if col in self.diagnosis_data.columns:
                dtype = self.diagnosis_data.schema[col]
                context += f"- {col} (Type: {dtype})\n"
        
        # Add sample data if requested
        if include_sample:
            sample_size = min(5, self.diagnosis_data.height)
            sample_df = self.diagnosis_data.select(relevant_columns).slice(0, sample_size)
            sample_data = sample_df.to_string()
            context += f"\nSample diagnosis data (first {sample_size} records):\n{sample_data}\n"
        
        return context
    
    def _get_brief_patient_context(self):
        """Get brief context about patient data."""
        key_columns = ["registry_id", "age", "gender"]
        available_columns = [col for col in key_columns if col in self.patient_data.columns]
        
        return f"Patient data includes {', '.join(available_columns)} and other attributes."
    
    def _get_brief_diagnosis_context(self):
        """Get brief context about diagnosis data."""
        key_columns = ["registry_id", "diagnosis", "diagnosis_date"]
        available_columns = [col for col in key_columns if col in self.diagnosis_data.columns]
        
        return f"Diagnosis data includes {', '.join(available_columns)} and other attributes."
    
    def _identify_relevant_columns(self, query, df):
        """Identify columns that might be relevant to the query."""
        query_terms = query.lower().split()
        relevant_columns = []
        
        # Add columns that match query terms
        for col in df.columns:
            if any(term in col.lower() for term in query_terms):
                relevant_columns.append(col)
        
        # Always include registry_id for joining
        if "registry_id" in df.columns and "registry_id" not in relevant_columns:
            relevant_columns.insert(0, "registry_id")
        
        # If not enough columns were found through direct matches, include important ones
        if len(relevant_columns) < 3:
            # For patient data, include common important columns
            if "age" in df.columns and "age" not in relevant_columns:
                relevant_columns.append("age")
            if "gender" in df.columns and "gender" not in relevant_columns:
                relevant_columns.append("gender")
            if "diagnosis" in df.columns and "diagnosis" not in relevant_columns:
                relevant_columns.append("diagnosis")
        
        # Include some columns even if we don't have many matches
        if len(relevant_columns) < 3:
            for col in df.columns[:5]:
                if col not in relevant_columns:
                    relevant_columns.append(col)
        
        # Limit to a reasonable number of columns
        return relevant_columns[:8]