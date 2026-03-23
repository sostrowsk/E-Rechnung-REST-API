#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

EXIT_CODE=0
log_error() {
    echo -e "\033[0;31m✗ $1\033[0m" >&2
    EXIT_CODE=1
}
log_success() {
    echo -e "\033[0;32m✓ $1\033[0m"
}
log_info() {
    echo -e "\033[1;33m$1\033[0m"
}

clean_python_cache() {
    log_info "Cleaning Python Cache"
    find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true
    find "$PROJECT_ROOT" -type f -name "*.pyo" -delete 2>/dev/null || true
    log_success "Python cache cleaned"
}

run_formatters() {
    if [[ "$FIX_MODE" == true ]]; then
        if uv run black src/ tests/; then
            log_success "Black formatting applied"
        else
            log_error "Black formatting failed"
        fi
        if uv run isort src/ tests/; then
            log_success "isort applied"
        else
            log_error "isort failed"
        fi
    else
        if uv run black src/ tests/ --check --diff; then
            log_success "Black check passed"
        else
            log_error "Black check failed (run with -f to fix)"
        fi
        if uv run isort src/ tests/ --check-only --diff; then
            log_success "isort check passed"
        else
            log_error "isort check failed (run with -f to fix)"
        fi
    fi
}

run_linters() {
    if uv run flake8 src/ tests/; then
        log_success "flake8 check passed"
    else
        log_error "flake8 check failed"
    fi
}

run_tests() {
    log_info "Running tests"
    if [[ ${#TEST_ARGS[@]} -gt 0 ]]; then
        if uv run pytest "${TEST_ARGS[@]}"; then
            log_success "Tests passed"
        else
            log_error "Tests failed"
        fi
    else
        if uv run pytest --cov --cov-report=term-missing; then
            log_success "Tests passed"
        else
            log_error "Tests failed"
        fi
    fi
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [FILES/TESTS]

Options:
    -h, --help       Show this help message
    -c, --check      Run checks only (no fixes, default)
    -f, --fix        Apply automatic fixes (black, isort)
    -t, --tests      Run tests only
    -l, --lint       Run linters only
    -a, --all        Run all checks and tests (default)
    --no-format      Skip formatting checks
    --no-lint        Skip linting
    --no-tests       Skip tests
    --clean-cache    Clean Python cache

Examples:
    $0                      # Run all checks and tests
    $0 -c                   # Check only, no fixes
    $0 -f                   # Apply fixes, then lint and test
    $0 -t tests/test_api.py # Run specific test only
    $0 -l                   # Lint only, no tests
EOF
}

FORMATTING=true
LINTING=true
TESTING=true
FIX_MODE=false
CLEAN_CACHE=false
TEST_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -c|--check)
            FIX_MODE=false
            shift
            ;;
        -f|--fix)
            FIX_MODE=true
            CLEAN_CACHE=true
            shift
            ;;
        -t|--tests)
            FORMATTING=false
            LINTING=false
            shift
            while [[ $# -gt 0 && ! "$1" =~ ^- ]]; do
                TEST_ARGS+=("$1")
                shift
            done
            ;;
        -l|--lint)
            TESTING=false
            shift
            ;;
        -a|--all)
            FORMATTING=true
            LINTING=true
            TESTING=true
            shift
            ;;
        --no-format)
            FORMATTING=false
            shift
            ;;
        --no-lint)
            LINTING=false
            shift
            ;;
        --no-tests)
            TESTING=false
            shift
            ;;
        --clean-cache)
            CLEAN_CACHE=true
            shift
            ;;
        *)
            TEST_ARGS+=("$1")
            shift
            ;;
    esac
done

trap 'echo -e "\n\033[0;31mScript interrupted!\033[0m"; exit 130' INT TERM

if [[ "$CLEAN_CACHE" == true ]]; then
    clean_python_cache
fi
if [[ "$FORMATTING" == true ]]; then
    run_formatters
fi
if [[ "$LINTING" == true ]]; then
    run_linters
fi
if [[ "$TESTING" == true ]]; then
    run_tests
fi

if [[ $EXIT_CODE -eq 0 ]]; then
    echo ""
    log_success "All checks passed!"
else
    echo ""
    log_error "Some checks failed"
fi
exit $EXIT_CODE
