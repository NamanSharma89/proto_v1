# app/utils/db.py
import psycopg2
import polars as pl
from psycopg2.extras import execute_values
from app.config.settings import AppConfig
from app.utils.logging import get_logger

logger = get_logger(__name__)

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

def get_db_connection():
    """Get a connection to the PostgreSQL database."""
    try:
        logger.debug(f"Creating database connection to {AppConfig.DB_HOST}:{AppConfig.DB_PORT}/{AppConfig.DB_NAME}")
        conn = psycopg2.connect(
            host=AppConfig.DB_HOST,
            database=AppConfig.DB_NAME,
            user=AppConfig.DB_USER,
            password=AppConfig.DB_PASSWORD,
            port=AppConfig.DB_PORT,
            # Set search path to explicitly use public schema
            options="-c search_path=public"
        )
        logger.debug("Database connection established successfully")
        
        # Ensure the search path is set to public
        cursor = conn.cursor()
        cursor.execute("SET search_path TO public;")
        conn.commit()
        cursor.close()
        
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}", exc_info=True)
        raise

def create_tables(conn, patient_df, diagnosis_df, drop_if_exists=False):
    """
    Create tables for patient data and diagnosis data with appropriate relationships.
    
    Args:
        conn: Database connection
        patient_df: Patient data DataFrame
        diagnosis_df: Diagnosis data DataFrame
        drop_if_exists: If True, drop existing tables before creating them (use only in development)
    """
    cursor = conn.cursor()
    
    try:
        # If drop_if_exists is True, drop the tables if they exist
        if drop_if_exists:
            logger.warning("DROP_IF_EXISTS flag is True. Dropping existing tables!")
            
            # Drop tables in reverse order (to handle foreign key constraints)
            logger.debug("Dropping diagnosis_details table if it exists")
            cursor.execute("DROP TABLE IF EXISTS public.diagnosis_details CASCADE;")
            
            logger.debug("Dropping patient_details table if it exists")
            cursor.execute("DROP TABLE IF EXISTS public.patient_details CASCADE;")
            
            conn.commit()
            logger.info("Existing tables dropped successfully")
    
        # Create tables
        logger.debug("Creating patient_details table")
        create_dynamic_table(conn, "patient_details", patient_df)
        logger.debug("patient_details table created or already exists")
        
        # Create diagnosis table with foreign key
        logger.debug("Creating diagnosis_details table")
        create_dynamic_table(conn, "diagnosis_details", diagnosis_df)
        logger.debug("diagnosis_details table created or already exists")
        
        # Add registry_id as Primary Key to patient_details table if it doesn't exist
        logger.debug("Setting registry_id as primary key on patient_details table")
        try:
            # Check if there's already a primary key on the table
            cursor.execute("""
            SELECT count(*) FROM pg_constraint 
            WHERE conrelid = 'public.patient_details'::regclass 
            AND contype = 'p';
            """)
            
            has_primary_key = cursor.fetchone()[0] > 0
            
            if has_primary_key:
                logger.debug("Primary key already exists on patient_details table")
                
                # Check if it's on registry_id
                cursor.execute("""
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = 'public.patient_details'::regclass
                AND i.indisprimary;
                """)
                
                pk_columns = [row[0] for row in cursor.fetchall()]
                logger.debug(f"Current primary key columns: {pk_columns}")
                
                # If registry_id is not part of the primary key, we'll drop it and recreate
                if "registry_id" not in pk_columns:
                    logger.debug("Dropping existing primary key to replace with registry_id")
                    # First get the constraint name
                    cursor.execute("""
                    SELECT conname FROM pg_constraint 
                    WHERE conrelid = 'public.patient_details'::regclass AND contype = 'p'
                    """)
                    constraint_name = cursor.fetchone()[0]
                    
                    # Now drop it using the actual name
                    cursor.execute(f"""
                    ALTER TABLE public.patient_details DROP CONSTRAINT IF EXISTS {constraint_name};
                    """)
                    
                    # Now add registry_id as primary key
                    cursor.execute("""
                    ALTER TABLE public.patient_details 
                    ADD CONSTRAINT pk_patient_registry_id PRIMARY KEY (registry_id);
                    """)
                    logger.debug("Primary key set to registry_id")
            else:
                # No primary key exists, add it on registry_id
                cursor.execute("""
                ALTER TABLE public.patient_details 
                ADD CONSTRAINT pk_patient_registry_id PRIMARY KEY (registry_id);
                """)
                logger.debug("Primary key constraint added on registry_id")
                
        except Exception as e:
            # If we can't add the constraint (e.g., due to duplicate registry_ids), log the error
            logger.warning(f"Could not set registry_id as primary key: {str(e)}")
            logger.warning("Foreign key relationship may be impacted. Check for duplicate registry_ids in patient data.")
        
        # Check if the foreign key already exists
        logger.debug("Checking if foreign key constraint exists")
        cursor.execute("""
        SELECT COUNT(*) FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_diagnosis_patient' 
        AND table_name = 'diagnosis_details'
        AND table_schema = 'public';
        """)
        
        fk_constraint_exists = cursor.fetchone()[0] > 0
        logger.debug(f"Foreign key constraint exists: {fk_constraint_exists}")
        
        if not fk_constraint_exists:
            # Add foreign key constraint
            logger.debug("Adding foreign key constraint")
            try:
                cursor.execute("""
                ALTER TABLE public.diagnosis_details 
                ADD CONSTRAINT fk_diagnosis_patient 
                FOREIGN KEY (registry_id) 
                REFERENCES public.patient_details (registry_id);
                """)
                logger.debug("Foreign key constraint added successfully")
            except Exception as e:
                logger.warning(f"Could not add foreign key constraint: {str(e)}")
                logger.warning("This may be due to lack of primary key or data integrity issues.")
        
        conn.commit()
        logger.debug("Schema changes committed")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating schema: {str(e)}", exc_info=True)
        raise
    finally:
        cursor.close()

def create_dynamic_table(conn, table_name, df):
    """
    Dynamically create a table based on DataFrame schema.
    
    Args:
        conn: Database connection
        table_name: Name of the table to create
        df: DataFrame containing the schema information
    """
    cursor = conn.cursor()
    
    try:
        # Start building SQL statement with schema explicitly defined
        create_table_sql = f"CREATE TABLE IF NOT EXISTS public.{table_name} (\n"
        
        # If table_name is patient_details, don't add id as primary key
        # since we'll use registry_id as the primary key
        if table_name == "patient_details":
            create_table_sql += "    id SERIAL,\n"  # Not PRIMARY KEY
        else:
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
        
        # Verify table was created
        cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        );
        """, (table_name,))
        
        exists = cursor.fetchone()[0]
        logger.debug(f"Table verification - {table_name} exists: {exists}")
        
    except Exception as e:
        logger.error(f"Error creating table {table_name}: {str(e)}", exc_info=True)
        raise
    finally:
        cursor.close()

def insert_data(conn, table_name, df):
    """
    Insert data into a table with validation.
    
    Args:
        conn: Database connection
        table_name: Name of the table to insert data into
        df: DataFrame containing the data to insert
        
    Returns:
        Dictionary containing insertion results including success/failure counts
    """
    cursor = conn.cursor()
    logger.info(f"Starting data validation and insertion for {table_name}")
    
    # Track statistics
    stats = {
        "total_records": df.height,
        "valid_records": 0,
        "rejected_records": 0,
        "error_reasons": {}
    }
    
    try:
        # Get column names from the dataframe
        columns = df.columns
        logger.debug(f"Columns for {table_name}: {columns}")
        
        # Get table schema from the database
        cursor.execute(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}' AND table_schema = 'public'
        """)
        db_columns = {row[0]: row[1] for row in cursor.fetchall()}
        logger.debug(f"Database schema for {table_name}: {db_columns}")
        
        # Validate records before insertion
        valid_records = []
        rejected_records = []
        
        # Convert Polars DataFrame to list of tuples
        all_records = [tuple(row) for row in df.to_numpy()]
        
        # Validation for different table types
        for record_idx, record in enumerate(all_records):
            try:
                # Basic validation
                if len(record) != len(columns):
                    raise ValueError(f"Record has {len(record)} values but should have {len(columns)}")
                
                # Table-specific validation
                if table_name == "patient_details":
                    # Ensure registry_id is not empty (needed for primary key)
                    registry_id_idx = columns.index("registry_id") if "registry_id" in columns else -1
                    if registry_id_idx >= 0:
                        if not record[registry_id_idx] or str(record[registry_id_idx]).strip() == "":
                            raise ValueError("Empty registry_id not allowed (primary key constraint)")
                
                elif table_name == "diagnosis_details":
                    # Ensure registry_id is not empty (needed for foreign key)
                    registry_id_idx = columns.index("registry_id") if "registry_id" in columns else -1
                    if registry_id_idx >= 0:
                        if not record[registry_id_idx] or str(record[registry_id_idx]).strip() == "":
                            raise ValueError("Empty registry_id not allowed (foreign key constraint)")
                
                # Type validation
                for col_idx, col_name in enumerate(columns):
                    if col_name in db_columns:
                        value = record[col_idx]
                        
                        # Skip null values
                        if value is None:
                            continue
                            
                        # Check numeric fields
                        if db_columns[col_name].startswith(('int', 'float', 'numeric', 'double', 'decimal')):
                            try:
                                if not isinstance(value, (int, float)) and value != '':
                                    float(value)  # Try to convert to validate
                            except (ValueError, TypeError):
                                raise ValueError(f"Invalid numeric value for {col_name}: {value}")
                
                # Record passes validation
                valid_records.append(record)
                
            except Exception as e:
                # Record fails validation
                rejected_records.append((record_idx, record, str(e)))
                
                # Track error reasons
                error_type = str(e)
                if error_type in stats["error_reasons"]:
                    stats["error_reasons"][error_type] += 1
                else:
                    stats["error_reasons"][error_type] = 1
        
        # Update validation stats
        stats["valid_records"] = len(valid_records)
        stats["rejected_records"] = len(rejected_records)
        
        # Log validation results
        if rejected_records:
            logger.warning(f"Validation completed with {len(rejected_records)} rejected records out of {len(all_records)}")
            # Log first 5 rejected records with reasons
            for i, (idx, record, reason) in enumerate(rejected_records[:5]):
                logger.warning(f"Rejected record #{idx}: {reason}")
                logger.debug(f"Record data: {record}")
            
            if len(rejected_records) > 5:
                logger.warning(f"... and {len(rejected_records) - 5} more rejected records")
        else:
            logger.info(f"All {len(valid_records)} records passed validation")
        
        # Proceed with insertion of valid records
        if valid_records:
            # Prepare SQL statement for execute_values
            sql = f"INSERT INTO public.{table_name} ({', '.join(columns)}) VALUES %s"
            
            logger.info(f"Inserting {len(valid_records)} valid records into public.{table_name}")
            
            # Use batch insertion for better performance
            try:
                execute_values(cursor, sql, valid_records)
                conn.commit()
                logger.info(f"Successfully inserted {len(valid_records)} records into {table_name}")
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error during insertion: {str(e)}")
                stats["insertion_error"] = str(e)
                stats["valid_records"] = 0  # Reset since insertion failed
                stats["rejected_records"] = df.height  # All records effectively rejected
        else:
            logger.warning(f"No valid records to insert into {table_name}")
        
        # Return detailed statistics
        return stats
    
    except Exception as e:
        logger.error(f"Error in insert_data for {table_name}: {str(e)}", exc_info=True)
        stats["error"] = str(e)
        return stats
    finally:
        cursor.close()