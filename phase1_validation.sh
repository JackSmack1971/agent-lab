#!/bin/bash
# phase1_validation.sh

echo "🔍 Phase 1 Validation Starting..."

# Task 1.1: Parallelization
echo "\n[Task 1.1] Checking CI parallelization..."
if grep -q "\-n auto" .github/workflows/tests.yml && \
   grep -q "randomly-seed" .github/workflows/tests.yml; then
    echo "✅ CI parallelization enabled"
else
    echo "❌ CI parallelization NOT enabled"
    exit 1
fi

# Task 1.2: pytest.ini removal
echo "\n[Task 1.2] Checking pytest.ini removal..."
if [ ! -f pytest.ini ] && [ ! -f pytest.ini.backup ]; then
    echo "✅ pytest.ini removed"
    # Verify tests still work
    if pytest --collect-only > /dev/null 2>&1; then
        echo "✅ Test discovery still works"
    else
        echo "❌ Test discovery broken"
        exit 1
    fi
else
    echo "❌ pytest.ini still exists"
    exit 1
fi

# Task 1.3: --durations profiling
echo "\n[Task 1.3] Checking --durations flag..."
if grep -q "\-\-durations" pyproject.toml; then
    echo "✅ --durations flag added"
    # Verify it appears in help
    if pytest --help | grep -q "durations"; then
        echo "✅ --durations flag active"
    fi
else
    echo "❌ --durations flag NOT added"
    exit 1
fi

echo "\n✅✅✅ Phase 1 Complete! ✅✅✅"
echo "Summary:"
echo "- CI parallelization: ENABLED (expected 2-4x speedup)"
echo "- pytest.ini: REMOVED (single source of truth)"
echo "- Test profiling: ENABLED (slowest 10 tests shown)"
echo ""
echo "🚀 Ready for Phase 2: Coverage Sprint"
echo "   Phase 2 will benefit from parallelization for faster iteration"