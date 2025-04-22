# app/utils/db.py
import psycopg2
import polars as pl
from psycopg2.extras import execute_values
from app.config.settings import AppConfig

def get_db_connection():
    """Get a connection to the Aurora PostgreSQL database."""
    conn = psycopg2.connect(
        host=AppConfig.DB_HOST,
        database=AppConfig.DB_NAME,
        user=AppConfig.DB_USER,
        password=AppConfig.DB_PASSWORD,
        port=AppConfig.DB_PORT
    )
    return conn

def _get_pg_type(polars_type):
    """Map Polars data types to PostgreSQL data types."""
    type_map = {
        pl.Int8: "SMALLINT",
        pl.Int16: "SMALLINT",
        pl.Int32: "INTEGER",
        pl.Int64: "BIGINT",
        pl.UInt8: "SMALLINT",
        pl.UInt16: "INTEGER",
        pl.UInt32: "BIGINT",
        pl.UInt64: "BIGINT",
        pl.Float32: "REAL",
        pl.Float64: "DOUBLE PRECISION",
        pl.Boolean: "BOOLEAN",
        pl.Utf8: "TEXT",
        pl.Date: "DATE",
        pl.Datetime: "TIMESTAMP",
        pl.Time: "TIME",
    }
    
    # Default to TEXT if type not found
    return type_map.get(polars_type, "TEXT")

def create_dynamic_table(conn, table_name, df):
    """
    Dynamically create a table based on DataFrame schema.
    
    Args:
        conn: Database connection
        table_name: Name of the table to create
        df: Polars DataFrame with the schema to use
    """
    cursor = conn.cursor()
    
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
    
    # Execute the SQL
    cursor.execute(create_table_sql)
    conn.commit()
    cursor.close()

def create_tables(conn, patient_df, diagnosis_df):
    """Create tables for patient data and diagnosis data with appropriate relationships."""
    # Create patient table
    create_dynamic_table(conn, "patient_details", patient_df)
    
    # Create diagnosis table with foreign key
    create_dynamic_table(conn, "diagnosis_details", diagnosis_df)
    
    # Add foreign key constraint if it doesn't exist
    cursor = conn.cursor()
    
    # First check if the foreign key already exists
    cursor.execute("""
    SELECT COUNT(*) FROM information_schema.table_constraints 
    WHERE constraint_name = 'fk_diagnosis_patient' 
    AND table_name = 'diagnosis_details';
    """)
    
    constraint_exists = cursor.fetchone()[0] > 0
    
    if not constraint_exists:
        # Add foreign key constraint
        cursor.execute("""
        ALTER TABLE diagnosis_details 
        ADD CONSTRAINT fk_diagnosis_patient 
        FOREIGN KEY (registry_id) 
        REFERENCES patient_details (registry_id);
        """)
    
    conn.commit()
    cursor.close()

def insert_data(conn, table_name, df):
    """Insert data into a table."""
    cursor = conn.cursor()
    
    # Get column names from the dataframe
    columns = df.columns
    
    # Prepare SQL statement
    placeholders = ', '.join(['%s'] * len(columns))
    sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
    
    # Convert Polars DataFrame to list of tuples
    values = [tuple(row) for row in df.to_numpy()]
    
    # Insert data
    execute_values(cursor, sql, values)
    
    conn.commit()
    cursor.close()
    
    return len(values)