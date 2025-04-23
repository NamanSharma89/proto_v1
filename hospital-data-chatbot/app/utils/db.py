# app/utils/db.py
import psycopg2
import polars as pl
from psycopg2.extras import execute_values
from app.config.settings import AppConfig
from app.utils.logging import get_logger 

def get_db_connection():
    """Get a connection to the Aurora PostgreSQL database."""
    logger = get_logger(__name__)
    try:
        logger.debug(f"Creating database connection to {AppConfig.DB_HOST}:{AppConfig.DB_PORT}/{AppConfig.DB_NAME}")
        conn = psycopg2.connect(
            host=AppConfig.DB_HOST,
            database=AppConfig.DB_NAME,
            user=AppConfig.DB_USER,
            password=AppConfig.DB_PASSWORD,
            port=AppConfig.DB_PORT
        )
        logger.debug("Database connection established successfully")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}", exc_info=True)
        raise

def create_tables(conn, patient_df, diagnosis_df):
    """Create tables for patient data and diagnosis data with appropriate relationships."""
    logger = get_logger(__name__)
    
    # Create patient table
    logger.debug("Creating patient_details table")
    create_dynamic_table(conn, "patient_details", patient_df)
    logger.debug("patient_details table created or already exists")
    
    # Create diagnosis table with foreign key
    logger.debug("Creating diagnosis_details table")
    create_dynamic_table(conn, "diagnosis_details", diagnosis_df)
    logger.debug("diagnosis_details table created or already exists")
    
    # Add foreign key constraint if it doesn't exist
    cursor = conn.cursor()
    
    try:
        # First check if the foreign key already exists
        logger.debug("Checking if foreign key constraint exists")
        cursor.execute("""
        SELECT COUNT(*) FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_diagnosis_patient' 
        AND table_name = 'diagnosis_details';
        """)
        
        constraint_exists = cursor.fetchone()[0] > 0
        logger.debug(f"Foreign key constraint exists: {constraint_exists}")
        
        if not constraint_exists:
            # Add foreign key constraint
            logger.debug("Adding foreign key constraint")
            cursor.execute("""
            ALTER TABLE diagnosis_details 
            ADD CONSTRAINT fk_diagnosis_patient 
            FOREIGN KEY (registry_id) 
            REFERENCES patient_details (registry_id);
            """)
            logger.debug("Foreign key constraint added successfully")
        
        conn.commit()
        logger.debug("Schema changes committed")
    except Exception as e:
        logger.error(f"Error updating schema: {str(e)}", exc_info=True)
        raise
    finally:
        cursor.close()

def create_dynamic_table(conn, table_name, df):
    """
    Dynamically create a table based on DataFrame schema.
    """
    logger = get_logger(__name__)
    cursor = conn.cursor()
    
    try:
        # Start building SQL statement
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
        create_table_sql += "    id SERIAL PRIMARY KEY,\n"
        
        # Add columns based on DataFrame schema
        for col_name, dtype in df.schema.items():
            # Convert column name to snake_case if not already
            col_name_snake = col_name.lower()
            pg_type = _get_pg_type(dtype)
            create_table_sql += f"    {col_name_snake} {pg_type},\n"
        
        # Add created_at timestamp
        create_table_sql += "    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
        create_table_sql += ");"
        
        # Log the full SQL statement
        logger.debug(f"Executing SQL: {create_table_sql}")
        
        # Execute the SQL
        cursor.execute(create_table_sql)
        conn.commit()
        logger.debug(f"Table {table_name} created or already exists")
    except Exception as e:
        logger.error(f"Error creating table {table_name}: {str(e)}", exc_info=True)
        raise
    finally:
        cursor.close()

def insert_data(conn, table_name, df):
    """Insert data into a table."""
    logger = get_logger(__name__)
    cursor = conn.cursor()
    
    try:
        # Get column names from the dataframe
        columns = df.columns
        logger.debug(f"Inserting data into {table_name} with columns: {columns}")
        
        # Prepare SQL statement
        placeholders = ', '.join(['%s'] * len(columns))
        sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # Convert Polars DataFrame to list of tuples
        values = [tuple(row) for row in df.to_numpy()]
        
        logger.debug(f"Inserting {len(values)} rows into {table_name}")
        if len(values) > 0:
            logger.debug(f"Sample row: {values[0]}")
        
        # Insert data
        if len(values) > 0:
            execute_values(cursor, sql, values)
            logger.debug(f"Data insertion completed, {len(values)} rows affected")
        else:
            logger.warning(f"No data to insert into {table_name}")
        
        conn.commit()
        return len(values)
    except Exception as e:
        logger.error(f"Error inserting data into {table_name}: {str(e)}", exc_info=True)
        raise
    finally:
        cursor.close()