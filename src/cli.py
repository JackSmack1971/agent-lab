"""CLI module for Agent Lab."""

import argparse
import json
import sys
import time

VERSION = "0.1.0"


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Agent Lab CLI")
    parser.add_argument('--verbose', action='store_true', help='Show progress indicators')
    parser.add_argument('--quiet', action='store_true', help='Minimal output')
    parser.add_argument('--task', type=str, help='Task to run')
    parser.add_argument('--config', type=str, help='Config file')
    parser.add_argument('--temperature', type=float, help='Temperature for generation (0.0-2.0)')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--version', action='version', version=f'Agent Lab {VERSION}')

    args = parser.parse_args()

    # Validate temperature
    if args.temperature is not None and not (0.0 <= args.temperature <= 2.0):
        print(f"Error: temperature must be between 0.0 to 2.0, got {args.temperature}", file=sys.stderr)
        sys.exit(1)

    # Validate config
    if args.config:
        try:
            with open(args.config, 'r') as f:
                pass  # just check exists
        except FileNotFoundError:
            print(f"ERROR: Config file '{args.config}' not found", file=sys.stderr)
            sys.exit(1)

    # Run task if specified
    if args.task:
        if args.verbose:
            print("Processing task...")
            for i in range(1, 11):
                print(f"Step {i}/10")
                time.sleep(0.01)  # simulate work
            print("✓ Complete")
        elif not args.quiet and not args.json:
            print(f"Running task: {args.task}")

        # Output result
        if args.json:
            result = {"status": "success", "result": f"Task {args.task} completed"}
            print(json.dumps(result))
        else:
            if not args.quiet:
                print(f"Task {args.task} completed")
            else:
                # For quiet mode, still output minimal result
                print(f"Task {args.task} completed")
    else:
        if not args.quiet and not args.json:
            print("No task specified")
        elif args.json:
            result = {"status": "error", "error": "No task specified"}
            print(json.dumps(result))


if __name__ == "__main__":
    main()