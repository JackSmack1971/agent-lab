#!/usr/bin/env python3
"""
Migration script to convert unittest.mock usage to pytest-mock.

This script performs automated migration from unittest.mock to pytest-mock
following the patterns described in GAP-006.
"""

import re
import os
from pathlib import Path
from typing import List, Tuple


def find_test_files() -> List[Path]:
    """Find all test files that use unittest.mock"""
    test_dirs = [
        Path('tests/unit'),
        Path('tests/integration'),
        Path('tests/src'),
        Path('tests/utils')
    ]

    test_files = []
    for test_dir in test_dirs:
        if test_dir.exists():
            test_files.extend(test_dir.rglob('test_*.py'))

    return test_files


def has_unittest_mock(content: str) -> bool:
    """Check if file uses unittest.mock"""
    return 'from unittest.mock import' in content or '@patch' in content


def remove_unittest_mock_imports(content: str) -> str:
    """Remove unittest.mock imports"""
    # Remove from unittest.mock import lines
    content = re.sub(r'from unittest\.mock import.*\n', '', content)

    # Remove individual imports from lines that only import from unittest.mock
    lines = content.split('\n')
    filtered_lines = []
    skip_next = False

    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue

        # Check for multi-line imports
        if line.strip().startswith('from unittest.mock import') and line.strip().endswith('\\'):
            skip_next = True
            continue

        # Skip lines that are just unittest.mock imports
        if re.match(r'^\s*from unittest\.mock import', line):
            continue

        filtered_lines.append(line)

    return '\n'.join(filtered_lines)


def extract_patch_decorators(content: str) -> List[Tuple[str, str]]:
    """Extract @patch decorators and their arguments"""
    patches = []
    lines = content.split('\n')

    for line in lines:
        line = line.strip()
        if line.startswith('@patch('):
            # Extract the patch target
            match = re.match(r'@patch\((["\'])([^"\']+)\1\)', line)
            if match:
                patches.append(match.group(2))

    return patches


def convert_patch_decorators(content: str) -> str:
    """Convert @patch decorators to mocker.patch() calls"""
    lines = content.split('\n')
    result_lines = []
    patches = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith('@patch('):
            # Extract patch target
            match = re.match(r'@patch\((["\'])([^"\']+)\1\)', line)
            if match:
                patches.append(match.group(2))
            i += 1
            continue

        elif line.startswith('def test_') and patches:
            # Found test function, add mocker parameter and patch calls
            # Insert mocker parameter
            func_match = re.match(r'(def test_\w+)\(([^)]*)\):', line)
            if func_match:
                func_name = func_match.group(1)
                params = func_match.group(2).strip()

                # Add mocker if not present
                if 'mocker' not in params:
                    if params:
                        params += ', mocker'
                    else:
                        params = 'mocker'

                result_lines.append(f'{func_name}({params}):')

                # Add patch calls at the beginning of function body
                indent = '    '
                for patch_target in reversed(patches):  # Reverse for correct order
                    result_lines.append(f'{indent}{patch_target.split(".")[-1]} = mocker.patch(\'{patch_target}\')')

                # Find the function body and adjust parameter order if needed
                # This is complex, so we'll handle it manually for now
                patches = []  # Reset for next function

            else:
                result_lines.append(lines[i])
        else:
            result_lines.append(lines[i])

        i += 1

    return '\n'.join(result_lines)


def convert_magic_mock_usage(content: str) -> str:
    """Convert MagicMock() to mocker.MagicMock()"""
    # Replace MagicMock() with mocker.MagicMock()
    # But only if mocker is available in the function scope
    # This is tricky to do automatically, so we'll leave it for manual review
    return content


def migrate_file(filepath: Path) -> bool:
    """Migrate a single test file"""
    print(f"Migrating: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Remove unittest.mock imports
    content = remove_unittest_mock_imports(content)

    # Convert @patch decorators (basic conversion)
    content = convert_patch_decorators(content)

    # Convert MagicMock usage (placeholder)
    content = convert_magic_mock_usage(content)

    if content != original:
        # Create backup
        backup_path = filepath.with_suffix('.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original)

        # Write migrated content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ Migrated: {filepath}")
        return True

    print(f"⚠️  No changes needed: {filepath}")
    return False


def main():
    """Main migration function"""
    print("Starting pytest-mock migration...")

    test_files = find_test_files()
    print(f"Found {len(test_files)} test files")

    migrated_count = 0
    for test_file in test_files:
        if test_file.exists():
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            if has_unittest_mock(content):
                if migrate_file(test_file):
                    migrated_count += 1

    print(f"\nMigration complete! Migrated {migrated_count} files.")
    print("⚠️  Manual review required for complex @patch conversions.")
    print("Backups created with .backup extension.")


if __name__ == '__main__':
    main()