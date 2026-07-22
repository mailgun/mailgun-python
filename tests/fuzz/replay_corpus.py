#!/usr/bin/env python3
import re
import sys
import importlib
from pathlib import Path

def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python replay_corpus.py <fuzzer_module_name> <corpus_dir>")
        print("Example: python replay_corpus.py fuzz_webhooks tests/fuzz/corpus/fuzz_webhooks")
        sys.exit(1)

    module_name = sys.argv[1]
    corpus_dir = Path(sys.argv[2])

    # Sanitize module name to prevent path traversal and arbitrary code execution
    if not re.fullmatch(r"fuzz_[a-zA-Z0-9_]+", module_name):
        print(f"Invalid fuzzer module name: {module_name}. Must match 'fuzz_*'")
        sys.exit(1)

    if not corpus_dir.is_dir():
        print(f"Directory not found: {corpus_dir}")
        sys.exit(1)

    # Dynamically import the specific TestOneInput function
    try:
        # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import
        fuzzer_module = importlib.import_module(f"tests.fuzz.{module_name}")
        TestOneInput = fuzzer_module.TestOneInput
    except ImportError:
        print(f"Could not import tests.fuzz.{module_name}")
        sys.exit(1)

    files = list(corpus_dir.iterdir())
    print(f"Replaying {len(files)} corpus files through {module_name}...")

    for filepath in files:
        if filepath.is_file():
            data = filepath.read_bytes()
            try:
                TestOneInput(data)
            except Exception:  # noqa: BLE001
                pass

    print("✅ Replay complete. Coverage data ready.")

if __name__ == "__main__":
    main()
