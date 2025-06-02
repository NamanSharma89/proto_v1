from setuptools import setup, find_packages

setup(
    name="hospital-data-chatbot-etl",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        "polars>=0.20.0",
        "psycopg2-binary>=2.9.0",
        "boto3>=1.26.0",
        "botocore>=1.29.0",
        "openpyxl>=3.1.0",
        "pandas>=2.0.0",  # Fallback for Excel reading
        "fastapi>=0.100.0",  # For optional API endpoints
        "uvicorn>=0.20.0",
        "pydantic>=2.0.0",
        "python-multipart>=0.0.6",
        "schedule>=1.2.0",  # For ETL scheduling
        "croniter>=1.3.0",  # For cron-like scheduling
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
        ],
        "cloud": [
            "kubernetes>=25.0.0",
            "celery>=5.3.0",  # For distributed task processing
            "redis>=4.5.0",   # For task queue
        ]
    },
    entry_points={
        "console_scripts": [
            "hospital-etl=app.main:main",
            "hospital-etl-schedule=scripts.schedule_etl:main",
        ],
    },
)