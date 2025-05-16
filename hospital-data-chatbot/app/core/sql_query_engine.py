# app/core/sql_query_engine.py
import re
from typing import Dict, List, Any, Tuple, Optional
import psycopg2
import psycopg2.extras
import polars as pl
from io import StringIO

from app.core.llm_connector import BedrockLLM
from app.utils.db import get_db_connection
from app.utils.logging import get_logger
from app.config.settings import AppConfig

import logging

logger = logging.getLogger(__name__)


class SQLQueryEngine:
    """
    Processes natural language queries by converting them to SQL using LLM,
    executing the SQL against the database, and formatting the results.
    
    Flow:
    User query -> LLM generates SQL -> SQL executed on DB -> Results returned to LLM -> Response formatted
    """

    def __init__(self):
        """Initialize the SQL Query Engine with LLM connector."""
        self.logger = get_logger(__name__)
        
        # Choose LLM implementation based on config
        if AppConfig.USE_OLLAMA:
            from app.core.ollama_connector import OllamaLLM
            self.llm = OllamaLLM()
            self.logger.info("Using Ollama for LLM processing")
        else:
            from app.core.llm_connector import BedrockLLM
            self.llm = BedrockLLM()
            self.logger.info("Using AWS Bedrock for LLM processing")
        
        self.db_schema = None
        
        # Load DB schema on initialization
        self._load_db_schema()
        
    def process_query(self, user_query: str) -> Dict[str, Any]:
        """
        Process a natural language query by:
        1. Converting it to SQL using LLM
        2. Validating the SQL for safety
        3. Executing the SQL against the database
        4. Formatting the results with LLM to include both SQL and results
        
        Args:
            user_query: Natural language query from the user
            
        Returns:
            Dictionary containing the response and metadata
        """
        self.logger.info(f"Processing natural language query: {user_query}")
        
        try:
            # Step 1: Convert natural language to SQL
            generated_sql, reasoning = self._generate_sql_from_query(user_query)
            
            if not generated_sql:
                return {
                    "response": "I couldn't generate a valid SQL query for your question. Could you rephrase it?",
                    "success": False,
                    "sql_generated": False
                }
            
            # Step 2: Validate SQL for safety
            is_safe, safety_message = self._validate_sql_safety(generated_sql)
            if not is_safe:
                self.logger.warning(f"Unsafe SQL query generated: {generated_sql}")
                return {
                    "response": f"I couldn't create a safe query for your question. {safety_message}",
                    "success": False,
                    "sql_generated": True,
                    "sql": generated_sql,
                    "reasoning": reasoning
                }
            
            # Step 3: Execute SQL query
            result_data, column_names, error = self._execute_sql_query(generated_sql)
            
            if error:
                self.logger.error(f"SQL execution error: {error}")
                
                # Try to get LLM to fix the query
                fixed_sql, fix_reasoning = self._fix_sql_query(generated_sql, error, user_query)
                
                if fixed_sql and fixed_sql != generated_sql:
                    self.logger.info(f"Attempting to execute fixed SQL: {fixed_sql}")
                    result_data, column_names, error = self._execute_sql_query(fixed_sql)
                    
                    if not error:
                        generated_sql = fixed_sql
                
                # If we still have an error after attempting to fix
                if error:
                    return {
                        "response": f"I generated a SQL query but encountered an error when executing it: {error}",
                        "success": False,
                        "sql_generated": True,
                        "sql": generated_sql,
                        "error": error
                    }
            
            # Step 4: Format the results using LLM, including SQL in the response
            if result_data:
                formatted_response = self._format_sql_results_with_query(
                    user_query, generated_sql, result_data, column_names
                )
            else:
                formatted_response = f"The query executed successfully but didn't return any results.\n\nSQL Query Used:\n```sql\n{generated_sql}\n```"
            
            # Prepare success response
            return {
                "response": formatted_response,
                "success": True,
                "sql_generated": True,
                "sql": generated_sql,
                "row_count": len(result_data) if result_data else 0,
                "column_names": column_names,
                "data": result_data
            }
                
        except Exception as e:
            self.logger.error(f"Error in SQL query engine: {str(e)}", exc_info=True)
            return {
                "response": f"I encountered an error while processing your query: {str(e)}",
                "success": False,
                "error": str(e)
            }
    
    def _load_db_schema(self) -> None:
        """
        Load database schema information to help with SQL generation.
        """
        try:
            self.logger.info("Loading database schema information")
            conn = get_db_connection()
            
            try:
                with conn.cursor() as cursor:
                    # Get list of tables
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                        AND table_type = 'BASE TABLE'
                    """)
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    # Get table structures
                    schema_info = {}
                    for table in tables:
                        cursor.execute(f"""
                            SELECT column_name, data_type, is_nullable
                            FROM information_schema.columns
                            WHERE table_schema = 'public' AND table_name = %s
                            ORDER BY ordinal_position
                        """, (table,))
                        
                        columns = []
                        for row in cursor.fetchall():
                            columns.append({
                                "name": row[0],
                                "type": row[1],
                                "nullable": row[2]
                            })
                        
                        schema_info[table] = columns
                        
                    # Get foreign key relationships
                    cursor.execute("""
                        SELECT
                            tc.table_name AS table_name, 
                            kcu.column_name AS column_name, 
                            ccu.table_name AS foreign_table_name,
                            ccu.column_name AS foreign_column_name
                        FROM 
                            information_schema.table_constraints AS tc 
                            JOIN information_schema.key_column_usage AS kcu
                              ON tc.constraint_name = kcu.constraint_name
                              AND tc.table_schema = kcu.table_schema
                            JOIN information_schema.constraint_column_usage AS ccu
                              ON ccu.constraint_name = tc.constraint_name
                              AND ccu.table_schema = tc.table_schema
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = 'public'
                    """)
                    
                    relationships = []
                    for row in cursor.fetchall():
                        relationships.append({
                            "table": row[0],
                            "column": row[1],
                            "foreign_table": row[2],
                            "foreign_column": row[3]
                        })
                    
                    # Store the complete schema information
                    self.db_schema = {
                        "tables": schema_info,
                        "relationships": relationships
                    }
                    
                    self.logger.info(f"Loaded schema information for {len(tables)} tables")
                    
            finally:
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Error loading database schema: {str(e)}", exc_info=True)
            self.db_schema = None
    
    def _generate_sql_prompt(self, user_query: str) -> str:
        """
        Generate a prompt for the LLM to convert natural language to SQL.
        
        Args:
            user_query: The natural language query from the user
            
        Returns:
            Formatted prompt for LLM
        """
        # Build schema information string
        schema_info = ""
        if self.db_schema:
            schema_info = "Database Schema:\n"
            
            # Add table information
            for table_name, columns in self.db_schema["tables"].items():
                schema_info += f"\nTABLE: {table_name}\n"
                schema_info += "Columns:\n"
                
                for col in columns:
                    nullable = "NULL" if col["nullable"] == "YES" else "NOT NULL"
                    schema_info += f"- {col['name']} ({col['type']}, {nullable})\n"
            
            # Add relationships
            if self.db_schema["relationships"]:
                schema_info += "\nRelationships:\n"
                for rel in self.db_schema["relationships"]:
                    schema_info += f"- {rel['table']}.{rel['column']} references {rel['foreign_table']}.{rel['foreign_column']}\n"
        
        # Build the prompt with more guidance on data types
        prompt = f"""
        You are an expert SQL developer helping to translate natural language queries about hospital patient data into SQL queries.
        
        {schema_info}
        
        IMPORTANT DATA TYPE HANDLING:
        - All columns are stored as TEXT in the database, even if they contain numeric values
        - When comparing numeric values, always use CAST or :: to convert text to numbers
        - For reliable conversion, use: CAST(NULLIF(column_name, '') AS NUMERIC)
        - This approach handles NULL values and empty strings properly
        
        The most important tables are:
        1. patient_details - Contains patient records with columns like registry_id, age, gender
        2. diagnosis_details - Contains diagnosis information related to patients, linked by registry_id
        
        User Query: {user_query}
        
        Your task:
        1. Analyze the request and determine what SQL is needed
        2. Write a PostgreSQL query that answers the user's question
        3. Ensure proper type conversion for any numeric comparisons
        4. Explain your reasoning step by step
        5. Ensure the query is secure and efficient
        
        Format your response as follows:
        
        REASONING:
        [Step by step explanation of how you're interpreting the query and constructing the SQL]
        
        SQL:
        [Your PostgreSQL query - only include the actual SQL code here]
        """
        
        return prompt
    
    def _generate_sql_from_query(self, user_query: str) -> Tuple[str, str]:
        """
        Use LLM to generate SQL from natural language query without extensive reasoning.
        
        Args:
            user_query: The natural language query from the user
            
        Returns:
            Tuple of (generated_sql, empty_reasoning)
        """
        prompt = f"""
        You are an expert SQL developer helping to translate natural language queries about hospital patient data into SQL queries.
        
        The database contains patient data with tables including:
        1. patient_details - Contains patient records with columns like registry_id, age, gender
        2. diagnosis_details - Contains diagnosis information related to patients, linked by registry_id
        
        IMPORTANT: When working with numeric columns (like age), use CAST(NULLIF(age, '') AS NUMERIC) for comparisons.
        
        User Query: {user_query}
        
        Please respond ONLY with the PostgreSQL query that would answer this question.
        No explanations or reasoning - just give me the SQL query.
        """
        
        try:
            # Get response from LLM
            response = self.llm.query(prompt, "")
            
            # Extract the SQL from the response
            # Look for code blocks first
            sql_match = re.search(r'```(?:sql)?\s*(.*?)\s*```', response, re.DOTALL)
            if sql_match:
                generated_sql = sql_match.group(1).strip()
            else:
                # Otherwise try to find a SELECT statement
                select_match = re.search(r'(SELECT\s+.*?;)', response, re.DOTALL, re.IGNORECASE)
                if select_match:
                    generated_sql = select_match.group(1).strip()
                else:
                    # Use the whole response if none of the above patterns match
                    generated_sql = response.strip()
            
            self.logger.info("SQL query generated successfully")
            self.logger.debug(f"Generated SQL: {generated_sql}")
            
            # Return SQL with empty reasoning
            return generated_sql, ""
            
        except Exception as e:
            self.logger.error(f"Error generating SQL: {str(e)}", exc_info=True)
            return "", f"Error generating SQL: {str(e)}"
    
    def _validate_sql_safety(self, sql_query: str) -> Tuple[bool, str]:
        """
        Validate that the SQL query is safe to execute.
        Attempt to fix common type conversion issues.
        
        Args:
            sql_query: The SQL query to validate
            
        Returns:
            Tuple of (is_safe, message)
        """
        # Keep the original query
        fixed_query = sql_query
        
        # Block dangerous operations
        dangerous_patterns = [
            (r'\bDROP\b', "DROP operations are not allowed"),
            (r'\bTRUNCATE\b', "TRUNCATE operations are not allowed"),
            (r'\bDELETE\b', "DELETE operations are not allowed"),
            (r'\bUPDATE\b', "UPDATE operations are not allowed"),
            (r'\bINSERT\b', "INSERT operations are not allowed"),
            (r'\bALTER\b', "ALTER operations are not allowed"),
            (r'\bCREATE\b', "CREATE operations are not allowed"),
            (r'\bGRANT\b', "GRANT operations are not allowed"),
            (r'\bREVOKE\b', "REVOKE operations are not allowed"),
            (r';.*?;', "Multiple SQL statements are not allowed"),
        ]
        
        # Check for dangerous patterns
        for pattern, message in dangerous_patterns:
            if re.search(pattern, sql_query, re.IGNORECASE):
                return False, message
        
        # Only allow SELECT statements
        if not re.match(r'^\s*SELECT', sql_query, re.IGNORECASE):
            return False, "Only SELECT statements are allowed"
        
        # Fix common type conversion issues directly on the input query
        # Pattern for simple comparisons like: WHERE age > 65
        numeric_comparison = re.compile(r'WHERE\s+(\w+)\s*([><=!]+)\s*(\d+(?:\.\d+)?)', re.IGNORECASE)
        sql_query = numeric_comparison.sub(
            r'WHERE CAST(NULLIF(\1, \'\') AS NUMERIC) \2 \3', 
            sql_query
        )
        
        # Pattern for numeric IN clauses: WHERE age IN (65, 70, 75)
        in_comparison = re.compile(r'WHERE\s+(\w+)\s+IN\s*\(([\d\s,\.]+)\)', re.IGNORECASE)
        sql_query = in_comparison.sub(
            r'WHERE CAST(NULLIF(\1, \'\') AS NUMERIC) IN (\2)', 
            sql_query
        )
        
        # Pattern for BETWEEN clauses: WHERE age BETWEEN 65 AND 75
        between_comparison = re.compile(
            r'WHERE\s+(\w+)\s+BETWEEN\s+(\d+(?:\.\d+)?)\s+AND\s+(\d+(?:\.\d+)?)', 
            re.IGNORECASE
        )
        sql_query = between_comparison.sub(
            r'WHERE CAST(NULLIF(\1, \'\') AS NUMERIC) BETWEEN \2 AND \3',
            sql_query
        )
        
        # If the query was modified, log it
        if sql_query != fixed_query:
            self.logger.info("SQL query automatically modified for better type handling")
            self.logger.debug(f"Original: {fixed_query}\nModified: {sql_query}")
        
        return True, "SQL query is safe"
    
    def _execute_sql_query(self, sql_query: str) -> Tuple[List[Dict[str, Any]], List[str], Optional[str]]:
        """
        Execute SQL query and return results.
        
        Args:
            sql_query: The SQL query to execute
            
        Returns:
            Tuple of (result_data, column_names, error_message)
        """
        try:
            self.logger.info("Executing SQL query")
            conn = get_db_connection()
            
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(sql_query)
                    results = cursor.fetchall()
                    
                    # Get column names
                    column_names = [desc[0] for desc in cursor.description] if cursor.description else []
                    
                    # Convert to list of dicts for easier processing
                    result_data = []
                    for row in results:
                        # Convert to dict while handling potential binary/non-serializable data
                        row_dict = {}
                        for i, col_name in enumerate(column_names):
                            value = row[i]
                            # Convert non-serializable types to strings
                            if isinstance(value, (bytes, bytearray)):
                                value = f"<binary data of length {len(value)}>"
                            row_dict[col_name] = value
                        result_data.append(row_dict)
                    
                    self.logger.info(f"SQL query executed successfully, returned {len(result_data)} rows")
                    return result_data, column_names, None
                    
            finally:
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Error executing SQL query: {str(e)}", exc_info=True)
            return [], [], str(e)
    
    def _format_sql_results(self, user_query: str, sql_query: str, 
                        result_data: List[Dict[str, Any]], column_names: List[str]) -> str:
        """
        Use LLM to format SQL results into natural language response.
        
        Args:
            user_query: Original user query
            sql_query: The SQL query that was executed
            result_data: The query results
            column_names: Names of the columns in the results
            
        Returns:
            Formatted natural language response
        """
        # Limit result size to avoid LLM token limits
        max_rows = 25
        truncated = len(result_data) > max_rows
        
        if truncated:
            result_sample = result_data[:max_rows]
            truncation_message = f"\n\nNote: Results limited to {max_rows} rows out of {len(result_data)} total."
        else:
            result_sample = result_data
            truncation_message = ""
        
        # Format results as a readable table for the prompt
        result_table = "Results:\n"
        
        # Convert to DataFrame for easier formatting
        # Create a Polars DataFrame from the result sample
        if result_sample:
            df = pl.DataFrame(result_sample)
            if not df.is_empty():
                # Format as a readable table using Polars - Fixed line below
                # Polars uses str() or .write_csv() to a StringIO object, not to_string()
                result_table += str(df)  # This is the correct way to convert Polars DataFrame to string
                result_table += "\n\n"
                result_table += f"Total rows returned: {len(result_data)}{truncation_message}"
            else:
                result_table = "No results returned."
        else:
            result_table = "No results returned."
        
        # Create the prompt for result formatting
        prompt = f"""
        You are an expert data analyst helping interpret SQL query results for hospital data.
        
        Original User Question: {user_query}
        
        SQL Query Used: {sql_query}
        
        {result_table}
        
        Total rows returned: {len(result_data)}{truncation_message if truncated else ""}
        
        Please provide a clear, comprehensive answer to the user's original question based on these results.
        Format your response in a conversational style, but include specific figures from the data.
        If helpful, include brief statistical summaries or relevant patterns in the data.
        """
        
        try:
            # Get formatted response from LLM
            response = self.llm.query(prompt, "")
            
            self.logger.info("Results formatted successfully")
            return response
            
        except Exception as e:
            self.logger.error(f"Error formatting results: {str(e)}", exc_info=True)
            
            # Fallback to basic formatting if LLM fails
            basic_response = f"Here are the results of your query:\n\n"
            if result_data:
                basic_response += f"Found {len(result_data)} records."
                if truncated:
                    basic_response += f" Showing first {max_rows}."
                    
                # Format a simple table using Polars if available
                try:
                    if result_sample:
                        df = pl.DataFrame(result_sample)
                        if not df.is_empty():
                            # Fixed line below - use str() instead of to_string()
                            basic_response += "\n\n" + str(df)
                        else:
                            # Manual formatting as fallback
                            basic_response += self._format_results_manually(result_sample, column_names)
                    else:
                        basic_response += "\n\nNo results to display."
                except Exception:
                    # Ultimate fallback: manual formatting
                    basic_response += self._format_results_manually(result_sample, column_names)
            else:
                basic_response += "No results found for your query."
                
            return basic_response
    
    def _format_results_manually(self, result_sample: List[Dict[str, Any]], column_names: List[str]) -> str:
        """
        Manually format results as a simple table when other methods fail.
        
        Args:
            result_sample: List of result dictionaries
            column_names: Names of the columns
            
        Returns:
            Formatted table as string
        """
        output = "\n\n"
        
        # Add header row
        for col in column_names:
            output += f"{col}\t"
        output += "\n"
        
        # Add separator
        output += "-" * (sum(len(col) + 8 for col in column_names)) + "\n"
        
        # Add data rows
        for row in result_sample:
            for col in column_names:
                value = row.get(col, "N/A")
                # Truncate long values
                if isinstance(value, str) and len(value) > 30:
                    value = value[:27] + "..."
                output += f"{value}\t"
            output += "\n"
        
        return output
    
    def _fix_sql_query(self, sql_query: str, error_message: str, user_query: str) -> Tuple[str, str]:
        """
        Use LLM to fix a failed SQL query based on the error message.
        
        Args:
            sql_query: The SQL query that failed
            error_message: The error message returned by the database
            user_query: The original user query
            
        Returns:
            Tuple of (fixed_sql_query, reasoning)
        """
        # Create prompt for fixing SQL with more guidance on type handling
        prompt = f"""
        You are an expert SQL developer fixing a PostgreSQL query that failed.
        
        Original User Query: {user_query}
        
        Failed SQL Query:
        ```sql
        {sql_query}
        ```
        
        Error Message: {error_message}
        
        Important notes for fixing this query:
        1. The 'age' column is stored as TEXT in the database, not as a number
        2. For numeric comparisons with text columns, use CAST or :: syntax
        3. Some values may have decimal points, so cast to FLOAT or NUMERIC first, then to INTEGER if needed
        4. For example, use: WHERE CAST(NULLIF(age, '') AS NUMERIC) > 65
        5. The NULLIF function handles empty strings that can't be converted to numbers
        
        Please fix the SQL query to resolve the error. Only return the corrected SQL query and your reasoning.
        
        Format your response as follows:
        
        REASONING:
        [Explain what was wrong with the original query and how you fixed it]
        
        SQL:
        [Your fixed PostgreSQL query - only include the actual SQL code here]
        """
        
        try:
            # Get fixed SQL from LLM
            response = self.llm.query(prompt, "")
            
            # Extract SQL and reasoning from the response
            sql_match = re.search(r'SQL:\s*(.*?)(?=$|\n\n)', response, re.DOTALL)
            reasoning_match = re.search(r'REASONING:\s*(.*?)(?=$|\n\nSQL:)', response, re.DOTALL)
            
            fixed_sql = sql_match.group(1).strip() if sql_match else ""
            reasoning = reasoning_match.group(1).strip() if reasoning_match else ""
            
            # Clean up SQL (remove markdown code block markers if present)
            fixed_sql = re.sub(r'^```sql\s*|\s*```$', '', fixed_sql)
            
            self.logger.info("SQL query fixed successfully")
            self.logger.debug(f"Fixed SQL: {fixed_sql}")
            
            return fixed_sql, reasoning
            
        except Exception as e:
            self.logger.error(f"Error fixing SQL: {str(e)}")
            return "", f"Error fixing SQL: {str(e)}" 

    def _format_sql_results_with_query(self, user_query: str, sql_query: str, 
                                result_data: List[Dict[str, Any]], column_names: List[str]) -> str:
        """
        Format SQL results into a response that includes both the SQL query and results.
        
        Args:
            user_query: Original user query
            sql_query: The SQL query that was executed
            result_data: The query results
            column_names: Names of the columns in the results
            
        Returns:
            Formatted natural language response with SQL query included
        """
        # Limit result size to avoid LLM token limits
        max_rows = 25
        truncated = len(result_data) > max_rows
        
        if truncated:
            result_sample = result_data[:max_rows]
            truncation_message = f"\n\nNote: Results limited to {max_rows} rows out of {len(result_data)} total."
        else:
            result_sample = result_data
            truncation_message = ""
        
        # Format results as a readable table
        result_table = "Results:\n"
        
        # Format results using Polars
        if result_sample:
            try:
                df = pl.DataFrame(result_sample)
                if not df.is_empty():
                    # Use str() for Polars DataFrames
                    result_table += str(df) 
                    result_table += f"\n\nTotal rows returned: {len(result_data)}{truncation_message}"
                else:
                    result_table = "No results returned."
            except Exception as e:
                self.logger.error(f"Error formatting results with Polars: {str(e)}", exc_info=True)
                # Fallback to manual formatting
                result_table += self._format_results_manually(result_sample, column_names)
        else:
            result_table = "No results returned."
        
        # Create the prompt for result formatting - explicitly request to include SQL
        prompt = f"""
        You are an expert SQL analyst helping interpret database query results.
        
        Original User Question: {user_query}
        
        SQL Query Used:
        ```sql
        {sql_query}
        ```
        
        {result_table}
        
        Please format your response as follows:
        1. First provide a clear, direct answer to the user's question based on the results
        2. Then include the SQL query that was used
        3. Finally provide a brief explanation of the results
        
        Keep your tone conversational and expressive. Make sure you explicitly include the SQL query code block in your response.
        """
        
        try:
            # Get formatted response from LLM
            response = self.llm.query(prompt, "")
            
            # If the response doesn't include the SQL query, add it
            if "```sql" not in response:
                response = f"{response}\n\nSQL Query Used:\n```sql\n{sql_query}\n```"
            
            self.logger.info("Results formatted successfully with SQL query included")
            return response
            
        except Exception as e:
            self.logger.error(f"Error formatting results: {str(e)}", exc_info=True)
            
            # Fallback to basic formatting if LLM fails, ensuring SQL is included
            basic_response = f"Here are the results of your query:\n\n"
            
            if result_data:
                basic_response += f"Found {len(result_data)} records."
                if truncated:
                    basic_response += f" Showing first {max_rows}."
                    
                # Format a simple table
                try:
                    if result_sample:
                        df = pl.DataFrame(result_sample)
                        if not df.is_empty():
                            basic_response += "\n\n" + str(df)
                        else:
                            # Manual formatting as fallback
                            basic_response += self._format_results_manually(result_sample, column_names)
                    else:
                        basic_response += "\n\nNo results to display."
                except Exception:
                    # Ultimate fallback: manual formatting
                    basic_response += self._format_results_manually(result_sample, column_names)
            else:
                basic_response += "No results found for your query."
            
            # Always include the SQL query in the fallback response
            basic_response += f"\n\nSQL Query Used:\n```sql\n{sql_query}\n```"
            
            return basic_response