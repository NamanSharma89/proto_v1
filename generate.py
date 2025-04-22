#!/usr/bin/env python3
import os
import argparse

def create_directory(path):
    """Create directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")

def create_file(path):
    """Create an empty file if it doesn't exist."""
    if not os.path.exists(path):
        with open(path, 'w') as f:
            pass  # Create empty file
        print(f"Created file: {path}")

def create_project_structure(base_dir):
    """Create the entire project structure."""
    # Create base directory
    create_directory(base_dir)
    
    # Create main directories
    dirs = [
        os.path.join(base_dir, "app"),
        os.path.join(base_dir, "app", "api"),
        os.path.join(base_dir, "app", "config"),
        os.path.join(base_dir, "app", "core"),
        os.path.join(base_dir, "app", "models"),
        os.path.join(base_dir, "app", "utils"),
        os.path.join(base_dir, "data", "raw"),
        os.path.join(base_dir, "data", "processed"),
        os.path.join(base_dir, "deploy"),
        os.path.join(base_dir, "tests"),
        os.path.join(base_dir, "notebooks"),
    ]
    
    for directory in dirs:
        create_directory(directory)
    
    # Create Python package __init__.py files
    init_files = [
        os.path.join(base_dir, "app", "__init__.py"),
        os.path.join(base_dir, "app", "api", "__init__.py"),
        os.path.join(base_dir, "app", "config", "__init__.py"),
        os.path.join(base_dir, "app", "core", "__init__.py"),
        os.path.join(base_dir, "app", "models", "__init__.py"),
        os.path.join(base_dir, "app", "utils", "__init__.py"),
        os.path.join(base_dir, "tests", "__init__.py"),
    ]
    
    for init_file in init_files:
        create_file(init_file)
    
    # Create main app files
    app_files = [
        os.path.join(base_dir, "app", "main.py"),
        os.path.join(base_dir, "app", "api", "routes.py"),
        os.path.join(base_dir, "app", "api", "middleware.py"),
        os.path.join(base_dir, "app", "config", "settings.py"),
        os.path.join(base_dir, "app", "core", "data_processor.py"),
        os.path.join(base_dir, "app", "core", "query_engine.py"),
        os.path.join(base_dir, "app", "core", "llm_connector.py"),
        os.path.join(base_dir, "app", "models", "data_models.py"),
        os.path.join(base_dir, "app", "utils", "aws.py"),
        os.path.join(base_dir, "app", "utils", "logging.py"),
        os.path.join(base_dir, "app", "utils", "math_utils.py"),
    ]
    
    for app_file in app_files:
        create_file(app_file)
    
    # Create deployment files
    deploy_files = [
        os.path.join(base_dir, "deploy", "cloudformation.yaml"),
        os.path.join(base_dir, "deploy", "sagemaker_config.json"),
        os.path.join(base_dir, "deploy", "bedrock_setup.sh"),
    ]
    
    for deploy_file in deploy_files:
        create_file(deploy_file)
    
    # Create test files
    test_files = [
        os.path.join(base_dir, "tests", "conftest.py"),
        os.path.join(base_dir, "tests", "test_data_processor.py"),
        os.path.join(base_dir, "tests", "test_query_engine.py"),
        os.path.join(base_dir, "tests", "test_llm_connector.py"),
    ]
    
    for test_file in test_files:
        create_file(test_file)
    
    # Create notebook files
    notebook_files = [
        os.path.join(base_dir, "notebooks", "data_exploration.ipynb"),
        os.path.join(base_dir, "notebooks", "model_evaluation.ipynb"),
    ]
    
    for notebook_file in notebook_files:
        create_file(notebook_file)
    
    # Create root files
    root_files = [
        os.path.join(base_dir, "README.md"),
        os.path.join(base_dir, "requirements.txt"),
        os.path.join(base_dir, "Dockerfile"),
        os.path.join(base_dir, ".gitignore"),
        os.path.join(base_dir, "setup.py"),
    ]
    
    for root_file in root_files:
        create_file(root_file)
    
    print(f"\nProject structure created successfully at: {os.path.abspath(base_dir)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate hospital data chatbot project structure")
    parser.add_argument("--dir", default="hospital-data-chatbot", help="Base directory for the project")
    args = parser.parse_args()
    
    create_project_structure(args.dir)