# Dependency Management Guide

## 🏗️ Overview

The Canza Platform uses a comprehensive dependency management system designed for a monorepo structure with shared packages, applications, and an SDK.

## 📁 Structure

```
canza-platform/
├── pyproject.toml                    # Root workspace configuration
├── packages/
│   ├── core/pyproject.toml          # Core orchestration package
│   ├── integrations/pyproject.toml  # Payment integrations package
│   └── utils/pyproject.toml         # Shared utilities package
├── sdk/
│   └── setup.py                     # SDK for PyPI distribution
├── applications/
│   └── capp/
│       └── requirements.txt         # Application-specific dependencies
└── scripts/
    └── setup.sh                     # Development environment setup
```

## 🔧 Configuration Files

### 1. Root `pyproject.toml`

**Purpose**: Manages the entire workspace with shared dependencies and development tools.

**Key Features**:
- **Workspace Configuration**: Defines all packages in the monorepo
- **Shared Dependencies**: Common dependencies used across all packages
- **Development Tools**: Unified configuration for black, isort, mypy, pytest
- **Optional Dependencies**: dev, test, docs, prod groups

**Usage**:
```bash
# Install workspace with dev dependencies
pip install -e ".[dev]"

# Install specific optional dependencies
pip install -e ".[test,docs]"
```

### 2. Package `pyproject.toml` Files

#### `packages/core/pyproject.toml`
**Purpose**: Core orchestration and consensus framework.

**Dependencies**:
- Core framework (pydantic, pydantic-settings)
- Async support (asyncio-mqtt, aioredis)
- Data processing (numpy, pandas, scikit-learn)
- Consensus and coordination (networkx, scipy)

**Usage**:
```bash
# Install core package
pip install -e packages/core

# Install with dev dependencies
pip install -e "packages/core[dev]"
```

#### `packages/integrations/pyproject.toml`
**Purpose**: Payment system integrations.

**Dependencies**:
- HTTP clients (aiohttp, httpx, requests)
- Security (cryptography, python-jose, passlib)
- Multi-currency support (forex-python, python-money)
- Geographic data (pycountry, geopy)

**Optional Dependencies**:
- `blockchain`: Web3 and Ethereum tools
- `mobile-money`: OAuth and Twilio integration
- `banking`: SOAP and XML processing

**Usage**:
```bash
# Install with blockchain support
pip install -e "packages/integrations[blockchain]"

# Install with all integrations
pip install -e "packages/integrations[blockchain,mobile-money,banking]"
```

### 3. SDK `setup.py`

**Purpose**: PyPI-distributable Canza Agent Framework SDK.

**Features**:
- **Complete Dependencies**: All necessary dependencies for agent development
- **Optional Groups**: dev, test, docs, integrations, full
- **Console Scripts**: Command-line tools for agent management
- **Package Data**: Type hints and configuration files

**Usage**:
```bash
# Install SDK
pip install canza-agents

# Install with all features
pip install "canza-agents[full]"

# Install for development
pip install "canza-agents[dev]"
```

### 4. Application `requirements.txt`

**Purpose**: Application-specific dependencies for the CAPP application.

**Features**:
- **FastAPI Application**: Web framework and server
- **Database**: SQLAlchemy, asyncpg, Redis
- **Security**: Authentication and encryption
- **Development**: Testing and code quality tools

**Usage**:
```bash
# Install application dependencies
pip install -r applications/capp/requirements.txt
```

## 🚀 Development Workflow

### 1. Initial Setup

```bash
# Run the setup script
./scripts/setup.sh

# This will:
# - Create virtual environment
# - Install workspace with dev dependencies
# - Install all packages in editable mode
# - Install application dependencies
# - Setup pre-commit hooks
# - Create environment files
```

### 2. Local Development

```bash
# Activate virtual environment
source venv/bin/activate

# Install workspace packages in editable mode
pip install -e ".[dev]"
pip install -e packages/core
pip install -e packages/integrations
pip install -e packages/utils
pip install -e sdk

# Install application dependencies
pip install -r applications/capp/requirements.txt
```

### 3. Package Development

```bash
# Work on core package
cd packages/core
pip install -e ".[dev]"
pytest

# Work on integrations package
cd packages/integrations
pip install -e ".[blockchain,dev]"
pytest

# Work on SDK
cd sdk
pip install -e ".[dev]"
pytest
```

### 4. Testing

```bash
# Run all tests
./scripts/test-all.sh

# Run specific package tests
pytest packages/core/tests/
pytest packages/integrations/tests/
pytest sdk/tests/

# Run with coverage
pytest --cov=packages/core
pytest --cov=packages/integrations
pytest --cov=sdk
```

## 📦 Dependency Categories

### Shared Dependencies (Root)
- **Core Framework**: pydantic, pydantic-settings
- **Data Processing**: numpy, pandas, scikit-learn
- **Logging & Monitoring**: structlog, prometheus-client
- **Utilities**: python-dotenv, click, rich
- **Multi-currency**: forex-python, python-money
- **Geographic**: pycountry, geopy

### Package-Specific Dependencies

#### Core Package
- **Async Support**: asyncio-mqtt, aioredis
- **Consensus**: networkx, scipy

#### Integrations Package
- **HTTP Clients**: aiohttp, httpx, requests
- **Security**: cryptography, python-jose, passlib
- **Blockchain**: web3, eth-account (optional)
- **Mobile Money**: requests-oauthlib, pyjwt, twilio (optional)
- **Banking**: zeep, xmltodict (optional)

#### Application
- **Web Framework**: fastapi, uvicorn
- **Database**: sqlalchemy, asyncpg, redis
- **Rate Limiting**: slowapi
- **Health Checks**: healthcheck

### Development Dependencies
- **Testing**: pytest, pytest-asyncio, pytest-cov, pytest-mock
- **Code Quality**: black, isort, flake8, mypy
- **Security**: bandit, safety
- **Documentation**: mkdocs, mkdocs-material, mkdocstrings

## 🔄 Dependency Resolution

### Workspace Dependencies
The root `pyproject.toml` defines shared dependencies that are available to all packages in the workspace.

### Package Dependencies
Each package can define its own dependencies and optional dependencies.

### Application Dependencies
Applications can specify their own dependencies while inheriting from workspace packages.

### Version Management
- **Shared Versions**: Common dependencies use consistent versions across packages
- **Flexible Ranges**: Most dependencies use `>=` to allow compatible updates
- **Lock Files**: Consider using `pip-tools` or `poetry` for production deployments

## 🛠️ Build and Distribution

### Local Development
```bash
# Install in editable mode
pip install -e ".[dev]"
pip install -e packages/core
pip install -e packages/integrations
pip install -e packages/utils
pip install -e sdk
```

### Package Building
```bash
# Build individual packages
cd packages/core && python -m build
cd packages/integrations && python -m build
cd sdk && python -m build
```

### SDK Distribution
```bash
# Build SDK for PyPI
cd sdk
python -m build
python -m twine upload dist/*
```

## 🔍 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure packages are installed in editable mode
2. **Version Conflicts**: Check for conflicting dependency versions
3. **Missing Dependencies**: Verify all optional dependencies are installed
4. **Build Errors**: Ensure build tools are installed (`pip install build`)

### Debugging Commands

```bash
# Check installed packages
pip list

# Check package dependencies
pip show canza-core
pip show canza-integrations
pip show canza-agents

# Verify imports
python -c "import packages.core; print('Core package OK')"
python -c "import packages.integrations; print('Integrations package OK')"
python -c "import sdk.canza_agents; print('SDK OK')"

# Check for conflicts
pip check
```

## 📚 Best Practices

1. **Use Editable Installs**: Always use `-e` flag for local development
2. **Group Dependencies**: Use optional dependency groups for different use cases
3. **Version Pinning**: Pin versions in production, use ranges in development
4. **Documentation**: Keep dependency documentation up to date
5. **Testing**: Test with minimal and full dependency sets
6. **Security**: Regularly update dependencies and run security scans

## 🎯 Summary

The dependency management system provides:

- ✅ **Shared Dependencies**: Common dependencies defined once at the root
- ✅ **Independent Packages**: Each package can be installed separately
- ✅ **Development Tools**: Unified development environment
- ✅ **SDK Distribution**: PyPI-ready SDK with comprehensive dependencies
- ✅ **Application Isolation**: Application-specific dependencies
- ✅ **Flexible Installation**: Optional dependency groups for different use cases
- ✅ **Local Development**: Editable installs for rapid development
- ✅ **Production Ready**: Proper versioning and dependency resolution

This structure enables efficient development, testing, and distribution of the Canza Platform components. 