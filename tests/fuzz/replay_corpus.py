#!/usr/bin/env python3
import sys
from pathlib import Path

# Import the target function directly from your fuzzer
from tests.fuzz.fuzz_client import TestOneInput


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python replay_corpus.py <corpus_dir>")
        sys.exit(1)

    corpus_dir = Path(sys.argv[1])
    if not corpus_dir.is_dir():
        print(f"Directory not found: {corpus_dir}")
        sys.exit(1)

    files = list(corpus_dir.iterdir())
    print(f"Replaying {len(files)} corpus files for coverage...")

    for filepath in files:
        if filepath.is_file():
            data = filepath.read_bytes()

            # Feed the data into the fuzzer harness
            try:
                TestOneInput(data)
            except Exception:  # noqa: BLE001
                # We expect crashes or handled errors here.
                # We only care about the lines of code reached.
                pass

    print("✅ Replay complete. Coverage data saved.")


if __name__ == "__main__":
    main()
