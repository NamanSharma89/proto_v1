# scripts/nightly_import.py
import requests
import os
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/nightly_import_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_nightly_import():
    """Run the nightly import process."""
    logger.info("Starting nightly import process")
    
    api_url = os.environ.get("API_URL", "http://localhost:8080")
    api_key = os.environ.get("API_KEY", "default_dev_key")
    
    try:
        # First, trigger data loading/processing
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # Trigger the import
        import_url = f"{api_url}/api/import-to-db"
        response = requests.post(import_url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Import completed successfully: {result}")
            return True
        else:
            logger.error(f"Import failed with status {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error during nightly import: {str(e)}")
        return False

if __name__ == "__main__":
    run_nightly_import()