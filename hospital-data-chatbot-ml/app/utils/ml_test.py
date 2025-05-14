# client_ml_demo.py
import requests
import time
import json

API_URL = "http://localhost:8080/api"
API_KEY = "your_api_key"  # Replace with your actual API key

def train_model():
    """Train a readmission prediction model."""
    url = f"{API_URL}/ml/train-model"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {
        "model_type": "readmission_prediction",
        "hyperparameters": {
            "objective": "binary:logistic",
            "num_round": "100",
            "max_depth": "6",
            "eta": "0.3",
            "eval_metric": "auc"
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        result = response.json()
        print(f"Training job started: {result['details']['job_name']}")
        return result['details']['job_name']
    else:
        print(f"Error starting training job: {response.text}")
        return None

def check_model_status(training_job_name):
    """Check the status of a training job."""
    url = f"{API_URL}/ml/model-status/{training_job_name}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"Training job status: {result['details']['status']}")
        return result['details']['status']
    else:
        print(f"Error checking training job status: {response.text}")
        return None

def deploy_model(training_job_name):
    """Deploy a trained model."""
    url = f"{API_URL}/ml/deploy-model"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {
        "training_job_name": training_job_name,
        "instance_type": "ml.t2.medium"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        result = response.json()
        print(f"Model deployment initiated: {result['details']['endpoint_name']}")
        return result['details']['endpoint_name']
    else:
        print(f"Error deploying model: {response.text}")
        return None

def get_patient_readmission_risk(patient_id):
    """Get readmission risk for a patient."""
    url = f"{API_URL}/ml/readmission-risk/{patient_id}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"Patient {patient_id} readmission risk: {result['risk_percentage']}%")
        print(f"Risk level: {result['risk_level']}")
        print("Key risk factors:")
        for factor in result['key_factors']:
            print(f"- {factor['factor']}: {factor['value']} (Impact: {factor['impact']})")
        return result
    else:
        print(f"Error getting readmission risk: {response.text}")
        return None

def main():
    """Run the ML workflow demo."""
    print("Starting ML workflow demo...")
    
    # Train the model
    training_job_name = train_model()
    if not training_job_name:
        return
    
    # Check status until complete
    status = check_model_status(training_job_name)
    while status not in ["Completed", "Failed", "Stopped"]:
        print("Waiting for training job to complete...")
        time.sleep(30)
        status = check_model_status(training_job_name)
    
    if status != "Completed":
        print(f"Training job did not complete successfully: {status}")
        return
    
    # Deploy the model
    endpoint_name = deploy_model(training_job_name)
    if not endpoint_name:
        return
    
    # Wait for deployment to complete
    print("Waiting for deployment to complete...")
    time.sleep(60)
    
    # Get readmission risk for a patient
    patient_id = "P12345"  # Replace with an actual patient ID
    risk_result = get_patient_readmission_risk(patient_id)
    
    print("\nML workflow demo completed!")

if __name__ == "__main__":
    main()