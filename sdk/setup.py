#!/usr/bin/env python3
"""
Setup script for Canza Agent Framework SDK
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Canza Agent Framework - AI-powered payment agent development toolkit"

# Read version from __init__.py
def get_version():
    init_path = os.path.join(os.path.dirname(__file__), "canza_agents", "__init__.py")
    if os.path.exists(init_path):
        with open(init_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("__version__"):
                    return line.split("=")[1].strip().strip('"\'')
    return "0.1.0"

setup(
    name="canza-agents",
    version=get_version(),
    author="Canza Team",
    author_email="team@canza.com",
    description="AI-powered payment agent development framework for cross-border payments",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/canza/canza-platform",
    project_urls={
        "Documentation": "https://docs.canza.com",
        "Bug Tracker": "https://github.com/canza/canza-platform/issues",
        "Source Code": "https://github.com/canza/canza-platform",
    },
    package_dir={"": "."},
    packages=find_packages(include=["canza_agents", "canza_agents.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    python_requires=">=3.9",
    
    # Core dependencies
    install_requires=[
        # Core Framework
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        
        # Async Support
        "asyncio-mqtt>=0.16.0",
        "aioredis>=2.0.0",
        
        # HTTP Client
        "aiohttp>=3.9.0",
        "httpx>=0.25.0",
        "requests>=2.31.0",
        
        # Data Processing
        "numpy>=1.25.0",
        "pandas>=2.1.0",
        "scikit-learn>=1.3.0",
        
        # Logging & Monitoring
        "structlog>=23.2.0",
        "prometheus-client>=0.19.0",
        
        # Utilities
        "python-dotenv>=1.0.0",
        "click>=8.1.0",
        "rich>=13.7.0",
        
        # Consensus and Coordination
        "networkx>=3.0",
        "scipy>=1.10.0",
        
        # Multi-currency Support
        "forex-python>=1.8",
        "python-money>=0.5",
        
        # Geographic & Currency Data
        "pycountry>=23.12.0",
        "geopy>=2.4.0",
    ],
    
    # Optional dependencies
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "black>=23.11.0",
            "isort>=5.12.0",
            "flake8>=6.1.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
            "bandit>=1.7.0",
            "safety>=2.0.0",
        ],
        "test": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "pytest-xdist>=3.0.0",
            "pytest-benchmark>=4.0.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
            "mkdocstrings[python]>=0.20.0",
            "mkdocs-autorefs>=0.4.0",
        ],
        "integrations": [
            # Blockchain
            "web3>=6.0.0",
            "eth-account>=0.9.0",
            "eth-typing>=3.0.0",
            "eth-utils>=2.0.0",
            
            # Mobile Money
            "requests-oauthlib>=1.3.0",
            "pyjwt>=2.8.0",
            "twilio>=8.0.0",
            
            # Banking
            "zeep>=4.2.0",
            "xmltodict>=0.13.0",
        ],
        "full": [
            # Include all optional dependencies
            "canza-agents[dev,test,docs,integrations]",
        ],
    },
    
    # Console scripts
    entry_points={
        "console_scripts": [
            "canza-agent=canza_agents.framework:main",
            "canza-orchestrator=canza_agents.orchestration:main",
            "canza-consensus=canza_agents.consensus:main",
            "canza-monitor=canza_agents.monitoring:main",
        ],
    },
    
    # Package data
    include_package_data=True,
    package_data={
        "canza_agents": [
            "py.typed",
            "*.pyi",
        ],
    },
    
    # Zip safe
    zip_safe=False,
    
    # Keywords
    keywords=[
        "ai", "agents", "payments", "blockchain", "africa", 
        "cross-border", "autonomous", "orchestration", "consensus",
        "mobile-money", "fintech", "financial", "optimization"
    ],
    
    # License
    license="MIT",
    
    # Platforms
    platforms=["any"],
    
    # Download URL
    download_url="https://github.com/canza/canza-platform/releases",
    
    # Provides
    provides=["canza_agents"],
    
    # Requires
    requires=[
        "python (>=3.9)",
    ],
    
    # Obsoletes
    obsoletes=[],
    
    # Project URLs
    project_urls={
        "Homepage": "https://github.com/canza/canza-platform",
        "Documentation": "https://docs.canza.com",
        "Repository": "https://github.com/canza/canza-platform",
        "Bug Tracker": "https://github.com/canza/canza-platform/issues",
        "Changelog": "https://github.com/canza/canza-platform/blob/main/CHANGELOG.md",
        "Funding": "https://github.com/sponsors/canza",
    },
) 