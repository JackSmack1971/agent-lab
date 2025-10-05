#!/usr/bin/env python3

with open('src/utils/keyboard_handler.py', 'r') as f:
    content = f.read()

# Find the exact problematic section and replace it
# Look for the pattern around line 348
lines = content.split('\n')

# Find the update_context method
start_idx = None
for i, line in enumerate(lines):
    if 'def update_context(self, **kwargs) -> None:' in line:
        start_idx = i
        break

if start_idx is None:
    print("Could not find update_context method")
    exit(1)

# Find the end of the method (next method definition or class end)
end_idx = None
for i in range(start_idx + 1, len(lines)):
    line = lines[i].strip()
    if line.startswith('def ') or line.startswith('class ') or (line.startswith('@') and 'staticmethod' in line):
        end_idx = i
        break

if end_idx is None:
    end_idx = len(lines)

# Extract the method
method_lines = lines[start_idx:end_idx]
method_content = '\n'.join(method_lines)

# Replace the problematic part
old_problematic = '''                try:
                    if hasattr(self._current_context, key):
                        setattr(self._current_context, key, value)
                    else:
                        logger.warning(f"Unknown context attribute: {key}")
                except ValidationError as e:
            logger.error(f"Shortcut validation failed: {e}")
            raise ValueError("Invalid shortcut data") from e
        except Exception as e:
                    logger.error(f"Failed to update context attribute {key}: {e}")
        except ValidationError as e:
            logger.error(f"Shortcut validation failed: {e}")
            raise ValueError("Invalid shortcut data") from e
        except Exception as e:
            logger.error(f"Context update iteration failed: {e}")'''

new_correct = '''                if hasattr(self._current_context, key):
                    try:
                        setattr(self._current_context, key, value)
                    except Exception as e:
                        logger.error(f"Failed to set context attribute {key}: {e}")
                        raise
                else:
                    logger.warning(f"Unknown context attribute: {key}")
        except Exception as e:
            logger.error(f"Context update failed: {e}")
            raise'''

if old_problematic in method_content:
    method_content = method_content.replace(old_problematic, new_correct)
    # Put it back
    lines[start_idx:end_idx] = method_content.split('\n')
    content = '\n'.join(lines)

    with open('src/utils/keyboard_handler.py', 'w') as f:
        f.write(content)

    print("Successfully fixed the update_context method")
else:
    print("Could not find the problematic section")