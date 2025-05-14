# scripts/test_ml_api.py
import requests
import json
import argparse
import time

def parse_args():
    parser = argparse.ArgumentParser(description='Test ML API integration')
    parser.add_argument('--api-url', type=str, required=True, 
                        help='ML API URL')
    parser.add_argument('--api-key', type=str, required=True,
                        help='ML API key')
    parser.add_argument('--patient-id', type=str, default='P12345',
                        help='Patient ID to test')
    return parser.parse_args()

def test_models_endpoint(api_url, api_key):
    """Test the /models endpoint."""
    print("\nTesting /models endpoint...")
    url = f"{api_url}/models"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        models = response.json()
        print(f"Success! Found {len(models)} models:")
        for model in models:
            print(f"  - {model['model_id']} (Type: {model['model_type']}, Accuracy: {model['accuracy']})")
        return True
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return False

def test_model_metadata(api_url, api_key, model_id="readmission-risk-xgboost-v1"):
    """Test the /models/{model_id} endpoint."""
    print(f"\nTesting /models/{model_id} endpoint...")
    url = f"{api_url}/models/{model_id}"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        metadata = response.json()
        print(f"Success! Model details:")
        print(f"  - ID: {metadata['model_id']}")
        print(f"  - Version: {metadata['version']}")
        print(f"  - Type: {metadata['model_type']}")
        print(f"  - Description: {metadata['description']}")
        print(f"  - Accuracy: {metadata['accuracy']}")
        print(f"  - Features: {', '.join(metadata['feature_names'][:5])}...")
        return True
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return False

def test_prediction(api_url, api_key, patient_id, model_id="readmission-risk-xgboost-v1"):
    """Test the /predict endpoint."""
    print(f"\nTesting /predict endpoint with patient {patient_id}...")
    url = f"{api_url}/predict"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    payload = {
        "model_id": model_id,
        "context": {
            "patient_id": patient_id,
            "include_explanations": True
        },
        "inputs": {
            "patient_id": patient_id
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        result = response.json()
        print(f"Success! Prediction results:")
        print(f"  - Risk Score: {result['prediction']['risk_percentage']}%")
        print(f"  - Risk Level: {result['prediction']['risk_level']}")
        print(f"  - Confidence: {result['confidence']}")
        
        if result.get('explanation'):
            print(f"  - Explanation Format: {result['explanation']['format']}")
            if result['explanation'].get('importance_scores'):
                scores = result['explanation']['importance_scores']
                print("  - Feature Importance:")
                for feature, score in list(scores.items())[:5]:
                    print(f"    - {feature}: {score:.4f}")
        
        return True
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return False

def main():
    args = parse_args()
    api_url = args.api_url
    api_key = args.api_key
    patient_id = args.patient_id
    
    print(f"Testing ML API at {api_url}")
    
    # Test each endpoint
    models_success = test_models_endpoint(api_url, api_key)
    metadata_success = test_model_metadata(api_url, api_key)
    prediction_success = test_prediction(api_url, api_key, patient_id)
    
    # Print summary
    print("\nTest Summary:")
    print(f"  - Models Endpoint: {'✅ PASS' if models_success else '❌ FAIL'}")
    print(f"  - Model Metadata Endpoint: {'✅ PASS' if metadata_success else '❌ FAIL'}")
    print(f"  - Prediction Endpoint: {'✅ PASS' if prediction_success else '❌ FAIL'}")
    
    # Overall status
    if models_success and metadata_success and prediction_success:
        print("\n✅ All tests passed! ML API is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the ML API.")
        return 1

if __name__ == "__main__":
    main()