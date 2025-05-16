# app/core/ollama_connector.py
import requests
import json
import re
from app.config.settings import AppConfig
from app.utils.logging import get_logger

class OllamaLLM:
    """Interface for Ollama LLM services."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.model = AppConfig.OLLAMA_MODEL
        self.base_url = AppConfig.OLLAMA_HOST
        self.logger.info(f"Initialized Ollama connector with model: {self.model} at {self.base_url}")
    
    def query(self, user_query, context, max_tokens=1000):
        """
        Send a query to the LLM with context information.
        
        Args:
            user_query: User's question
            context: Context information (schema, etc.)
            max_tokens: Maximum tokens to generate
            
        Returns:
            LLM response text
        """
        prompt = self._format_prompt(user_query, context)
        
        try:
            # Format the request for Ollama API
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,  # Disable streaming to get a single response
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.95,
                    "num_predict": max_tokens
                }
            }
            
            self.logger.debug(f"Sending request to Ollama")
            
            # Send request to Ollama
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            # Check if request was successful
            response.raise_for_status()
            
            # Get the raw response for debugging
            raw_response = response.text
            self.logger.debug(f"Raw response from Ollama: {raw_response[:100]}...")
            
            # Parse the JSON response
            try:
                result = json.loads(raw_response)
                full_response = result.get("response", "")
                
                # Extract SQL and reasoning using regex
                reasoning_match = re.search(r'REASONING:\s*(.*?)(?=\s*SQL:|$)', full_response, re.DOTALL)
                sql_match = re.search(r'SQL:\s*(.*?)(?=$)', full_response, re.DOTALL)
                
                reasoning = reasoning_match.group(1).strip() if reasoning_match else ""
                sql = sql_match.group(1).strip() if sql_match else ""
                
                self.logger.debug(f"Extracted SQL: {sql[:100]}...")
                
                # Return the full response for now - the SQL query engine will parse out the SQL portion
                return full_response
                
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON parsing error: {str(e)}")
                # If JSON parsing fails, just return the raw response
                return raw_response
            
        except Exception as e:
            self.logger.error(f"Error querying Ollama: {str(e)}")
            return f"Sorry, I encountered an error processing your request: {str(e)}"
    
    def _format_prompt(self, query, context):
        """Format the prompt for the text-to-SQL task."""
        return f"""
        You are an SQL developer specialized in helping to translate natural language queries about hospital patient data into SQL queries.
        
        {context}
        
        User Query: {query}
        
        Your task:
        1. Analyze the request and determine what SQL is needed
        2. Write a PostgreSQL query that answers the user's question
        3. Explain your reasoning step by step
        4. Ensure the query is secure and efficient
        
        Format your response as follows:
        
        REASONING:
        [Step by step explanation of how you're interpreting the query and constructing the SQL]
        
        SQL:
        [Your PostgreSQL query - only include the actual SQL code here]
        """