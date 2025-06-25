from setuptools import setup, find_packages

setup(
    name="aws-multiregion-ecommerce",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "aws-cdk-lib>=2.0.0",
        "constructs>=10.0.0",
        "boto3>=1.26.0"
    ],
    python_requires=">=3.9",
)