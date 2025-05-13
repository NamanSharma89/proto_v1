# app/utils/calculation_handler.py
import re
import polars as pl

class CalculationHandler:
    """Handles calculations requested by the LLM."""
    
    def __init__(self, patient_data, diagnosis_data):
        self.datasets = {
            "patient_details": patient_data,
            "diagnosis_details": diagnosis_data
        }
    
    def process_response(self, llm_response):
        """
        Process the LLM response and execute any calculation requests.
        
        Args:
            llm_response: The response from the LLM
            
        Returns:
            Processed response with calculations executed
        """
        # Pattern to find calculation requests
        pattern = r'\[CALCULATE: ([^\]]+)\]'
        
        # Find all calculation requests
        calculation_requests = re.findall(pattern, llm_response)
        
        processed_response = llm_response
        
        # Execute each calculation
        for calc_request in calculation_requests:
            calc_result = self._execute_calculation(calc_request)
            
            # Replace the calculation request with the result
            processed_response = processed_response.replace(
                f"[CALCULATE: {calc_request}]", 
                str(calc_result)
            )
            
        return processed_response
    
    def _execute_calculation(self, calc_request):
        """Execute a specific calculation request."""
        try:
            # Parse dataset, operation and column
            parts = calc_request.split('.')
            if len(parts) != 2:
                return "Error: Invalid calculation format. Use dataset.operation(column)"
            
            dataset_name = parts[0].strip()
            operation_part = parts[1].strip()
            
            if dataset_name not in self.datasets:
                return f"Error: Unknown dataset '{dataset_name}'"
            
            df = self.datasets[dataset_name]
            
            # Parse operation and column
            if "(" in operation_part and ")" in operation_part:
                operation = operation_part.split("(")[0].strip()
                column = operation_part.split("(")[1].split(")")[0].strip()
                
                # Handle special case for count()
                if operation == "count" and column == "":
                    return df.height
                
                # Make sure column exists (except for operations that don't require it)
                if column and column not in df.columns:
                    return f"Error: Column '{column}' not found in {dataset_name}"
                
                # Execute standard calculations
                if operation == "mean" and column:
                    result = df.select(pl.col(column).mean()).item()
                    return f"{result:.2f}" if isinstance(result, float) else result
                
                elif operation == "min" and column:
                    return df.select(pl.col(column).min()).item()
                
                elif operation == "max" and column:
                    return df.select(pl.col(column).max()).item()
                
                elif operation == "sum" and column:
                    result = df.select(pl.col(column).sum()).item()
                    return f"{result:.2f}" if isinstance(result, float) else result
                
                elif operation == "median" and column:
                    result = df.select(pl.col(column).median()).item()
                    return f"{result:.2f}" if isinstance(result, float) else result
                
                elif operation == "std" and column:
                    result = df.select(pl.col(column).std()).item()
                    return f"{result:.2f}" if isinstance(result, float) else result
                
                elif operation == "count_unique" and column:
                    return df.select(pl.col(column).n_unique()).item()
                
                # Special operation for diagnosis counts by patient
                elif operation == "count_by_patient" and dataset_name == "diagnosis_details":
                    # Group by registry_id and count
                    if "registry_id" not in df.columns:
                        return "Error: registry_id column not found for patient grouping"
                    
                    result = df.group_by("registry_id").agg(pl.count().alias("diagnosis_count"))
                    summary = (
                        f"Min diagnoses per patient: {result.select(pl.min('diagnosis_count')).item()}, "
                        f"Max: {result.select(pl.max('diagnosis_count')).item()}, "
                        f"Avg: {result.select(pl.mean('diagnosis_count')).item():.2f}"
                    )
                    return summary
            
            return "Error: Unsupported operation"
            
        except Exception as e:
            return f"Error executing calculation: {str(e)}"