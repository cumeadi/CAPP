#!/bin/bash

# Canza Platform Development Environment Setup Script
# This script sets up the complete development environment for the Canza Platform monorepo

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    local python_version=$(python3 --version 2>&1 | awk '{print $2}')
    local major=$(echo $python_version | cut -d. -f1)
    local minor=$(echo $python_version | cut -d. -f2)
    
    if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 9 ]); then
        print_error "Python 3.9 or higher is required. Found: $python_version"
        exit 1
    fi
    
    print_success "Python version: $python_version"
}

# Function to check Node.js version
check_node_version() {
    if ! command_exists node; then
        print_error "Node.js is not installed. Please install Node.js 18 or higher."
        exit 1
    fi
    
    local node_version=$(node --version | sed 's/v//')
    local major=$(echo $node_version | cut -d. -f1)
    
    if [ "$major" -lt 18 ]; then
        print_error "Node.js 18 or higher is required. Found: $node_version"
        exit 1
    fi
    
    print_success "Node.js version: $node_version"
}

# Function to check Git
check_git() {
    if ! command_exists git; then
        print_error "Git is not installed. Please install Git."
        exit 1
    fi
    
    print_success "Git is available"
}

# Function to create virtual environment
create_venv() {
    print_status "Creating Python virtual environment..."
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists. Removing..."
        rm -rf venv
    fi
    
    python3 -m venv venv
    print_success "Virtual environment created"
}

# Function to activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    print_success "Virtual environment activated and pip upgraded"
}

# Function to install Python dependencies
install_python_deps() {
    print_status "Installing Python dependencies..."
    
    # Install the workspace in editable mode with dev dependencies
    pip install -e ".[dev]"
    
    # Install workspace packages in editable mode
    print_status "Installing workspace packages in editable mode..."
    pip install -e "packages/core"
    pip install -e "packages/integrations"
    pip install -e "packages/utils"
    pip install -e "sdk"
    
    # Install application-specific dependencies
    print_status "Installing application dependencies..."
    pip install -r "applications/capp/requirements.txt"
    
    print_success "Python dependencies installed"
}

# Function to install frontend dependencies
install_frontend_deps() {
    print_status "Installing frontend dependencies..."
    
    cd applications/capp/capp-frontend
    
    # Check if package.json exists
    if [ ! -f "package.json" ]; then
        print_error "package.json not found in applications/capp/capp-frontend"
        exit 1
    fi
    
    # Install npm dependencies
    npm install
    
    cd ../../..
    print_success "Frontend dependencies installed"
}

# Function to setup pre-commit hooks
setup_pre_commit() {
    print_status "Setting up pre-commit hooks..."
    
    if command_exists pre-commit; then
        pre-commit install
        pre-commit install --hook-type commit-msg
        print_success "Pre-commit hooks installed"
    else
        print_warning "pre-commit not found. Skipping pre-commit setup."
    fi
}

# Function to create environment files
create_env_files() {
    print_status "Creating environment files..."
    
    # Create .env.example if it doesn't exist
    if [ ! -f ".env.example" ]; then
        cat > .env.example << EOF
# Canza Platform Environment Configuration

# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/canza_platform
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your-secret-key-here

# Blockchain Configuration
APTOS_NODE_URL=https://fullnode.mainnet.aptoslabs.com
APTOS_PRIVATE_KEY=your-private-key-here
APTOS_ACCOUNT_ADDRESS=your-account-address-here

# Agent Configuration
AGENT_TIMEOUT_SECONDS=60
AGENT_RETRY_ATTEMPTS=3
AGENT_CONSENSUS_THRESHOLD=0.7

# Monitoring Configuration
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001

# Development Configuration
DEBUG=true
LOG_LEVEL=INFO
EOF
        print_success "Created .env.example"
    fi
    
    # Create .env if it doesn't exist
    if [ ! -f ".env" ]; then
        cp .env.example .env
        print_success "Created .env (copy from .env.example)"
        print_warning "Please update .env with your actual configuration values"
    fi
}

# Function to run initial tests
run_initial_tests() {
    print_status "Running initial tests..."
    
    # Run basic import tests
    python -c "
import sys
try:
    import packages.core
    import packages.integrations
    import packages.utils
    import sdk.canza_agents
    import applications.capp
    print('✓ All packages import successfully')
except ImportError as e:
    print(f'✗ Import error: {e}')
    sys.exit(1)
"
    
    print_success "Initial tests passed"
}

# Function to display setup summary
display_summary() {
    echo
    print_success "🎉 Canza Platform development environment setup complete!"
    echo
    echo "📁 Project Structure:"
    echo "  ├── packages/          # Shared packages"
    echo "  ├── applications/      # Applications (CAPP)"
    echo "  ├── sdk/              # Canza Agent Framework"
    echo "  ├── examples/         # Usage examples"
    echo "  └── docs/             # Documentation"
    echo
    echo "🚀 Next Steps:"
    echo "  1. Activate virtual environment: source venv/bin/activate"
    echo "  2. Start backend: python -m applications.capp.main"
    echo "  3. Start frontend: cd applications/capp/capp-frontend && npm start"
    echo "  4. Run tests: ./scripts/test-all.sh"
    echo
    echo "📚 Documentation:"
    echo "  - Platform Overview: docs/platform-overview.md"
    echo "  - SDK Documentation: sdk/README.md"
    echo "  - CAPP Application: applications/capp/README.md"
    echo
    echo "🔧 Development Commands:"
    echo "  - Install dev dependencies: pip install -e '.[dev]'"
    echo "  - Run tests: pytest"
    echo "  - Format code: black . && isort ."
    echo "  - Type checking: mypy ."
    echo "  - Lint code: flake8 ."
    echo
}

# Main setup function
main() {
    echo "🚀 Setting up Canza Platform development environment..."
    echo
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    check_python_version
    check_node_version
    check_git
    
    # Create and activate virtual environment
    create_venv
    activate_venv
    
    # Install dependencies
    install_python_deps
    install_frontend_deps
    
    # Setup development tools
    setup_pre_commit
    
    # Create environment files
    create_env_files
    
    # Run initial tests
    run_initial_tests
    
    # Display summary
    display_summary
}

# Run main function
main "$@" 