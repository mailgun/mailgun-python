# Mailgun Python SDK: Performance & Architecture

This document outlines the architectural decisions made to ensure the Mailgun Python SDK remains blazingly fast and memory-efficient.

If you are contributing to this repository, please review these principles before modifying core routing, transport, or instantiation logic.

## Core Optimizations

### 1. High-Concurrency Transport Layer (`httpx` & Context Management)

We replaced the legacy `requests` library with `httpx` to modernize network I/O and enforce strict connection pooling.

- **Native AsyncIO:** The new `AsyncClient` allows for true non-blocking asynchronous throughput, reducing median request latency by effectively eliminating thread context-switching overhead.
- **Context Manager Enforcement:** The `Client` now implements `__enter__` and `__exit__`. By enforcing `with Client(...) as client:`, we guarantee the connection pool is cleanly closed, preventing OS socket leaks in long-running production environments.

### 2. Immutable URL Baking & Routing (`routes.py`)

String manipulation and regex compilation are historically slow operations in Python.

- **Constant Folding (O(1) Access):** Base API URLs (`/v3`, `/v4`, etc.) are pre-compiled and baked into the client's memory (`__slots__`) upon instantiation. The SDK completely avoids string concatenation during high-volume request loops.
- **State Machine Pre-Warming:** All API path resolution patterns are defined as pre-compiled `re.Pattern` objects, eliminating per-request compilation overhead.

### 3. Strict Memory Allocation (`__slots__`)

To prevent memory bloat in high-throughput microservices, the SDK enforces `__slots__` inheritance across the entire class hierarchy (`BaseClient`, `Client`, `AsyncClient`, `Endpoint`).

- **Memory Density:** Removing the dynamic `__dict__` drastically reduces the RAM footprint of each instantiated client and lowers Garbage Collection (GC) pauses during concurrent workloads.

______________________________________________________________________

## Benchmarks (v1.6.0 vs. Current)

Our internal `pytest-benchmark` and `cProfile` suites verify these architectural gains.

| Metric                        | v1.6.0 (Baseline) | Optimized Architecture | Delta           |
| :---------------------------- | :---------------- | :--------------------- | :-------------- |
| **Routing Speed (CPU Time)**  | ~17.61 µs         | **~0.84 µs**           | **~21x Faster** |
| **Async Throughput (Median)** | ~5.91 ms          | **~4.06 ms**           | **~31% Faster** |
| **Sync Throughput (Median)**  | ~20.2 ms          | **~10.5 ms**           | **~48% Faster** |

*Note: Benchmarks measure network-isolated internal overhead. Sync throughput showed massive improvements (~48%) after enforcing strict `__slots__` memory isolation.*

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
