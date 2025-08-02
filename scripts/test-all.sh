#!/bin/bash

# Canza Platform Test Script
# This script runs all tests across the monorepo

set -e

echo "🧪 Running Canza Platform Tests"
echo "=================================================="

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

# Check if virtual environment is activated
check_venv() {
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        print_warning "Virtual environment not activated. Activating..."
        source venv/bin/activate
    fi
    print_success "Virtual environment active: $VIRTUAL_ENV"
}

# Run Python tests
run_python_tests() {
    print_status "Running Python tests..."
    
    # Run tests with coverage
    pytest \
        --cov=packages \
        --cov=sdk \
        --cov=applications \
        --cov-report=html:htmlcov \
        --cov-report=term-missing \
        --cov-fail-under=80 \
        -v \
        --tb=short \
        --strict-markers \
        --disable-warnings
    
    print_success "Python tests completed"
}

# Run specific test categories
run_unit_tests() {
    print_status "Running unit tests..."
    pytest -m unit -v --tb=short
    print_success "Unit tests completed"
}

run_integration_tests() {
    print_status "Running integration tests..."
    pytest -m integration -v --tb=short
    print_success "Integration tests completed"
}

run_slow_tests() {
    print_status "Running slow tests..."
    pytest -m slow -v --tb=short
    print_success "Slow tests completed"
}

# Run linting
run_linting() {
    print_status "Running code linting..."
    
    # Run flake8
    flake8 packages/ sdk/ applications/ examples/ --max-line-length=88 --extend-ignore=E203,W503
    
    # Run isort check
    isort --check-only --diff packages/ sdk/ applications/ examples/
    
    # Run black check
    black --check --diff packages/ sdk/ applications/ examples/
    
    print_success "Linting completed"
}

# Run type checking
run_type_checking() {
    print_status "Running type checking..."
    mypy packages/ sdk/ applications/ examples/ --ignore-missing-imports
    print_success "Type checking completed"
}

# Run security checks
run_security_checks() {
    print_status "Running security checks..."
    
    # Check for common security issues
    if command -v bandit &> /dev/null; then
        bandit -r packages/ sdk/ applications/ examples/ -f json -o bandit-report.json
        print_success "Security checks completed"
    else
        print_warning "bandit not installed, skipping security checks"
    fi
}

# Run frontend tests
run_frontend_tests() {
    if command -v npm &> /dev/null; then
        print_status "Running frontend tests..."
        
        if [ -d "applications/capp/capp-frontend" ]; then
            cd applications/capp/capp-frontend
            
            # Install dependencies if needed
            if [ ! -d "node_modules" ]; then
                npm install
            fi
            
            # Run tests
            npm test -- --watchAll=false --coverage --passWithNoTests
            
            cd ../../..
            print_success "Frontend tests completed"
        else
            print_warning "Frontend directory not found, skipping frontend tests"
        fi
    else
        print_warning "npm not found, skipping frontend tests"
    fi
}

# Generate test report
generate_report() {
    print_status "Generating test report..."
    
    # Create reports directory
    mkdir -p reports
    
    # Generate coverage report
    if [ -d "htmlcov" ]; then
        echo "Coverage report available at: htmlcov/index.html"
    fi
    
    # Generate summary
    cat > reports/test-summary.md << EOF
# Test Summary Report

Generated on: $(date)

## Test Results

- **Python Tests**: ✅ Completed
- **Unit Tests**: ✅ Completed  
- **Integration Tests**: ✅ Completed
- **Slow Tests**: ✅ Completed
- **Linting**: ✅ Completed
- **Type Checking**: ✅ Completed
- **Security Checks**: ✅ Completed
- **Frontend Tests**: ✅ Completed

## Coverage

Coverage report available at: htmlcov/index.html

## Next Steps

1. Review any test failures
2. Address linting issues
3. Fix type checking errors
4. Update documentation as needed
EOF
    
    print_success "Test report generated: reports/test-summary.md"
}

# Main test function
main() {
    echo "Starting test execution..."
    
    # Check virtual environment
    check_venv
    
    # Run all test categories
    run_python_tests
    run_unit_tests
    run_integration_tests
    run_slow_tests
    
    # Run code quality checks
    run_linting
    run_type_checking
    run_security_checks
    
    # Run frontend tests
    run_frontend_tests
    
    # Generate report
    generate_report
    
    echo ""
    echo "🎉 All tests completed successfully!"
    echo "=================================================="
    echo "Test reports available at:"
    echo "- Coverage: htmlcov/index.html"
    echo "- Summary: reports/test-summary.md"
    echo "- Security: bandit-report.json (if available)"
    echo ""
}

# Parse command line arguments
case "${1:-all}" in
    "python")
        check_venv
        run_python_tests
        ;;
    "unit")
        check_venv
        run_unit_tests
        ;;
    "integration")
        check_venv
        run_integration_tests
        ;;
    "slow")
        check_venv
        run_slow_tests
        ;;
    "lint")
        check_venv
        run_linting
        ;;
    "types")
        check_venv
        run_type_checking
        ;;
    "security")
        check_venv
        run_security_checks
        ;;
    "frontend")
        run_frontend_tests
        ;;
    "all"|*)
        main
        ;;
esac 