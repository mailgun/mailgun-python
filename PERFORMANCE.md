# Mailgun Python SDK: Performance & Architecture

This document outlines the architectural decisions made to ensure the Mailgun Python SDK remains blazingly fast and memory-efficient.

If you are contributing to this repository, please review these principles before modifying core routing, transport, or instantiation logic.

## Core Optimizations

### 1. High-Concurrency Transport Layer (`httpx` & Context Management)

We replaced the legacy `requests` library with `httpx` to modernize network I/O and enforce strict connection pooling.

- **Native AsyncIO:** The new `AsyncClient` allows for true non-blocking asynchronous throughput, reducing median request latency by ~15% by eliminating thread context-switching overhead.
- **Context Manager Enforcement:** The `Client` now implements `__enter__` and `__exit__`. By enforcing `with Client(...) as client:`, we guarantee the `httpx` connection pool is cleanly closed. While pool teardown introduces a slight latency overhead during client destruction, it completely eliminates OS socket leaks in long-running production environments.

### 2. Pre-Compiled Static Routing (`routes.py`)

String manipulation and regex compilation are historically slow operations in Python.

- **State Machine Pre-Warming:** We introduced a standalone `routes.py` module. All API path resolution patterns (`DOMAIN_REGEX`, `VERSION_REGEX`) are defined here as pre-compiled `re.Pattern` objects.
- **Zero Per-Request Overhead:** By extracting regex compilation to the module level, the `build_url` execution path only evaluates pre-warmed C-level state machines, accelerating internal routing by over 15x.

### 3. The Zero-I/O Literal Lazy Router (`client.py`)

Traditional Python packages suffer a "Cold Boot" penalty when importing the main client triggers a cascade of sub-module file reads.

- **Zero Startup I/O:** Handler modules are imported strictly *inside* the `_load_handler` function body. They are not compiled from disk until the exact moment an API route is requested.
- **SAST Compliance:** Explicit literal `from ... import ...` statements prove to static analysis tools that Arbitrary Code Execution is impossible, securing the CI/CD pipeline without needing security suppressions.

### 4. Slot-Based Memory Allocation (`__slots__`)

All core classes (`Client`, `Endpoint`, `AsyncEndpoint`) strictly define `__slots__`.

- **Memory Density:** Removing the dynamic `__dict__` drastically reduces the RAM footprint of each instantiated client.

______________________________________________________________________

## Benchmarks (v1.6.0 vs. Current)

Our internal `pytest-benchmark` and `cProfile` suites verify these architectural gains.

| Metric                        | v1.6.0 (Baseline) | Optimized Architecture | Delta            |
| :---------------------------- | :---------------- | :--------------------- | :--------------- |
| **Routing Speed (CPU Time)**  | ~17.61 µs         | **~1.14 µs**           | **15.4x Faster** |
| **Cold-Boot Startup Time**    | ~0.254 s          | **~0.200 s**           | **21.2% Faster** |
| **Async Throughput (Median)** | ~5.91 ms          | **~5.03 ms**           | **15% Faster**   |

*Note: Synchronous throughput micro-benchmarks may show higher variance compared to v1.6.0. This is an expected artifact of the new `__exit__` context manager safely tearing down `httpx` connection pools during test iterations, trading micro-benchmark speed for production socket safety.*

______________________________________________________________________

## Profiling the Codebase

If you are modifying core internal logic, you must verify that you have not introduced I/O regressions or memory leaks.

**To profile Cold-Boot initialization:**

```bash
python tests/test_boot.py
```

**To benchmark the routing and throughput performance**

```bash
pytest tests/test_perf.py --benchmark-compare
```
