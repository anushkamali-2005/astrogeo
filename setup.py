"""Setup script for astrogeo-ai-mlops package."""

from pathlib import Path
from setuptools import setup, find_packages

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read requirements
def read_requirements(filename: str) -> list:
    """Read requirements from file."""
    requirements_path = this_directory / filename
    with open(requirements_path, encoding="utf-8") as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#") and not line.startswith("-r")
        ]

setup(
    name="astrogeo-ai-mlops",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Production-ready MLOps platform with Agentic AI and Geospatial Analytics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/astrogeo-ai-mlops",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/astrogeo-ai-mlops/issues",
        "Documentation": "https://astrogeo-ai-mlops.readthedocs.io",
        "Source Code": "https://github.com/yourusername/astrogeo-ai-mlops",
    },
    packages=find_packages(where=".", include=["src*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: GIS",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: FastAPI",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10,<3.12",
    install_requires=read_requirements("requirements.txt"),
    extras_require={
        "dev": read_requirements("requirements-dev.txt"),
    },
    entry_points={
        "console_scripts": [
            "astrogeo=src.api.main:run",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.toml"],
    },
    zip_safe=False,
)