from setuptools import setup, find_packages

setup(
    name="flightops",
    version="1.0.0",
    description="FlightOps - Airline Operations Management System",
    packages=find_packages(where="services"),
    package_dir={"": "services"},
    python_requires=">=3.11",
    install_requires=[
        "fastapi==0.111.0",
        "uvicorn==0.30.1",
        "pydantic==2.7.1",
        "httpx==0.27.0",
        "python-dotenv==1.0.1",
        "psycopg[binary,pool]==3.2.1",
        "prometheus-client==0.20.0",
        "loguru==0.7.2",
        "openai==1.40.3",
        "tiktoken==0.7.0",
    ],
)
