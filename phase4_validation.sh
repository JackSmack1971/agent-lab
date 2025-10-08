#!/bin/bash
# phase4_validation.sh

echo "🏗️ Phase 4 Infrastructure Validation..."

FAILURES=0

# Task 4.1: caplog
echo "\n[4.1] Checking caplog tests..."
CAPLOG_COUNT=$(grep -r "caplog" tests/ | wc -l)
if [ $CAPLOG_COUNT -ge 5 ]; then
    echo "✅ caplog: ${CAPLOG_COUNT} tests found"
else
    echo "❌ caplog: Only ${CAPLOG_COUNT} tests (need ≥5)"
    FAILURES=$((FAILURES + 1))
fi

# Task 4.2: capsys
echo "\n[4.2] Checking capsys tests..."
CAPSYS_COUNT=$(grep -r "capsys" tests/ | wc -l)
if [ $CAPSYS_COUNT -ge 5 ]; then
    echo "✅ capsys: ${CAPSYS_COUNT} tests found"
else
    echo "❌ capsys: Only ${CAPSYS_COUNT} tests (need ≥5)"
    FAILURES=$((FAILURES + 1))
fi

# Task 4.3: pytest-mock
echo "\n[4.3] Checking pytest-mock migration..."
UNITTEST_MOCK=$(grep -r "from unittest.mock import" tests/ | wc -l)
MOCKER=$(grep -r "def test_.*mocker" tests/ | wc -l)

if [ $UNITTEST_MOCK -eq 0 ] && [ $MOCKER -ge 10 ]; then
    echo "✅ pytest-mock: Migration complete (${MOCKER} tests)"
else
    echo "❌ pytest-mock: ${UNITTEST_MOCK} unittest.mock imports remain"
    echo "   mocker fixture used in ${MOCKER} tests (need ≥10)"
    FAILURES=$((FAILURES + 1))
fi

# Task 4.4: Hypothesis
echo "\n[4.4] Checking Hypothesis expansion..."
HYPOTHESIS_COUNT=$(grep -r "@given" tests/ | wc -l)
if [ $HYPOTHESIS_COUNT -ge 10 ]; then
    echo "✅ Hypothesis: ${HYPOTHESIS_COUNT} property tests found"
else
    echo "❌ Hypothesis: Only ${HYPOTHESIS_COUNT} tests (need ≥10)"
    FAILURES=$((FAILURES + 1))
fi

# Task 4.5: tmp_path_factory
echo "\n[4.5] Checking tmp_path_factory..."
if grep -q "tmp_path_factory" tests/conftest.py; then
    echo "✅ tmp_path_factory: Fixture defined"
else
    echo "❌ tmp_path_factory: Fixture not found"
    FAILURES=$((FAILURES + 1))
fi

# Task 4.6: Test naming
echo "\n[4.6] Checking test naming quality..."
# Count descriptive names (>30 chars)
DESCRIPTIVE=$(grep -r "def test_" tests/ | awk '{print length($2)}' | awk '$1 > 30' | wc -l)
TOTAL=$(grep -r "def test_" tests/ | wc -l)
PERCENT=$((DESCRIPTIVE * 100 / TOTAL))

if [ $PERCENT -ge 60 ]; then
    echo "✅ Test naming: ${PERCENT}% are descriptive"
else
    echo "⚠️  Test naming: Only ${PERCENT}% are descriptive (target: ≥60%)"
    echo "   (This is a soft requirement - OK to pass with lower %)"
fi

# Summary
echo "\n${'='*60}"
if [ $FAILURES -eq 0 ]; then
    echo "✅✅✅ Phase 4 COMPLETE ✅✅✅"
    echo "All infrastructure improvements validated!"
    exit 0
else
    echo "❌ Phase 4 has ${FAILURES} failing requirements"
    echo "Review failures above and address before completion"
    exit 1
fi