import os
from pathlib import Path

def pre_mutation(context):
    """
    Skip files that shouldn't be mutated

    Reasoning:
    - Test files don't need mutation (we're testing the tests!)
    - UI code has low mutation value (mostly presentation)
    - Generated code shouldn't be mutated
    """
    filename = context.filename

    # Skip test files
    if "test_" in filename or filename.endswith("conftest.py"):
        context.skip = True
        return

    # Skip UI components (low value for mutation testing)
    if "src/ui" in filename or "src/components/ui" in filename:
        context.skip = True
        return

    # Skip generated files
    if "__pycache__" in filename or ".pyc" in filename:
        context.skip = True
        return

# Define paths to mutate (critical business logic only)
paths_to_mutate = [
    "agents/runtime.py",
    "agents/models.py",
    "services/agent_service.py",
    "src/services/",
    "src/models/",
]

# Mutation configuration
mutmut_config = {
    # Disable low-value mutators
    "disable_mutators": [
        "string",  # String mutations rarely find bugs
        "number"   # Number mutations can be too sensitive
    ],

    # Use targeted mutations only
    "enable_mutators": [
        "operator",      # +, -, *, /, >, <, ==, etc.
        "keyword",       # if, while, for, return, etc.
        "exception",     # try/except/raise
    ]
}

def post_mutation(context):
    """
    Custom logic after mutation

    Could be used for:
    - Logging mutations
    - Custom filtering
    - Integration with CI
    """
    pass