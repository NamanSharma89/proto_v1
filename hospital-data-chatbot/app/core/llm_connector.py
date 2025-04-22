import boto3
import json
from app.config.settings import AppConfig

class BedrockLLM:
    """Interface for AWS Bedrock LLM services."""
    
    def __init__(self):
        self.model_id = AppConfig.BEDROCK_MODEL_ID
        self.client = boto3.client('bedrock-runtime')
    
    def query(self, user_query, context, max_tokens=1000):
        """
        Send a query to the LLM with context information.
        """
        prompt = self._format_prompt(user_query, context)
        
        # For Claude models in Bedrock
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })
        
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=body
            )
            
            response_body = json.loads(response.get('body').read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            print(f"Error querying LLM: {str(e)}")
            return f"Sorry, I encountered an error processing your request: {str(e)}"
    
    def _format_prompt(self, query, context):
        """Format the prompt for the LLM."""
        return f"""
        You are a helpful assistant specialized in analyzing hospital patient data.
        
        Context information about the hospital patient records:
        {context}
        
        User query: {query}
        
        Please analyze the data and provide a clear, concise, and accurate answer.
        If calculations are involved, show your reasoning step by step.
        If the data doesn't contain information to answer the query, please state that clearly.
        """