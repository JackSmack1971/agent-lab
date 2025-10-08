import ast
import re
from pathlib import Path

def suggest_better_name(func_name, docstring):
    """Suggest improved name based on docstring"""
    if not docstring:
        return None

    # Simple heuristic to generate descriptive name
    # Look for patterns like "Test that ..." or "Test ..." followed by behavior

    doc_lower = docstring.lower().strip()

    # Remove "test that" or "test" prefix
    if doc_lower.startswith("test that "):
        behavior_desc = docstring[10:].strip()
    elif doc_lower.startswith("test "):
        behavior_desc = docstring[5:].strip()
    else:
        behavior_desc = docstring.strip()

    # Extract key parts - simple approach: take first few words
    words = behavior_desc.split()
    if len(words) >= 3:
        # Try to form test_<subject>_<action>_<outcome> or similar
        # For example, "creating ShortcutContext" -> test_shortcut_context_creation_succeeds
        # This is basic - manual review recommended
        suggestion = f"test_{'_'.join(words[:3]).lower().replace('.', '').replace(',', '')}"
        # Ensure it's valid python identifier
        suggestion = re.sub(r'[^a-zA-Z0-9_]', '_', suggestion)
        return suggestion

    return None  # Manual naming still recommended

# Scan all test files
for test_file in Path('tests').rglob('test_*.py'):
    # Parse AST
    with open(test_file) as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
            docstring = ast.get_docstring(node)
            if docstring and len(node.name) < 30:
                suggestion = suggest_better_name(node.name, docstring)
                if suggestion:
                    print(f"{test_file}:{node.lineno}")
                    print(f"  Current:  {node.name}")
                    print(f"  Suggest:  {suggestion}")
                    print(f"  Docstring: {docstring[:60]}...")