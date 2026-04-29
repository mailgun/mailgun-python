# Mailgun Python SDK: Performance & Architecture

This document outlines the architectural decisions made to ensure the Mailgun Python SDK remains blazingly fast, memory-efficient, and secure.

If you are contributing to this repository, please review these principles before modifying core routing, transport, or instantiation logic.

## Core Optimizations

### 1. Constant-Time (O(1)) Dictionary Dispatch (`routes.py`)

String manipulation, dynamic imports (`importlib`), and sequential regex evaluations are historically slow in Python.

- **Static Dispatch:** Base API URLs (`/v3`, `/v4`, etc.) and handler functions are pre-mapped in immutable dictionaries (`EXACT_ROUTES`, `PREFIX_ROUTES`).
- **Impact:** The SDK completely avoids string concatenation and dynamic resolution during high-volume request loops, increasing routing speed by over **12x**.

### 2. High-Concurrency Transport Layer (`httpx` & `__slots__`)

- **Native AsyncIO & Connection Pooling:** The `AsyncClient` allows for true non-blocking throughput. Both clients enforce connection pooling to prevent OS socket exhaustion.
- **Memory Density (`__slots__`):** By defining `__slots__` on `Endpoint` and `Client` classes, we block Python from creating dynamic `__dict__` hash tables. This drastically reduces the RAM footprint of each instantiated client and lowers *Garbage Collection (GC)* pauses during concurrent workloads.

### 3. Cold-Boot Initialization & Lazy Loading

- **Deferred Regex Compilation:** Legacy SDK versions compiled multiple `re.Pattern` objects upon module import. By wrapping these in `@functools.lru_cache(maxsize=1)` and returning an immutable `MappingProxyType`, the SDK defers expensive AST parsing until the exact moment it is needed, shaving ~15-30ms off the initial application startup time.

______________________________________________________________________

## Benchmarks (v1.6.0 vs. v1.7.0)

Our internal `pytest-benchmark` and `cProfile` suites verify these architectural gains. Tests were executed on CPython 3.13 (Darwin 64-bit).

| Metric                      | v1.6.0 (Baseline) | v1.7.0 (Current) | Delta             |
| :-------------------------- | :---------------- | :--------------- | :---------------- |
| **Cold Boot Time**          | ~0.232 s          | **~0.201 s**     | **~13% Faster**   |
| **Routing Speed (Mean)**    | ~17.98 µs         | **~1.39 µs**     | **~12.9x Faster** |
| **Async Throughput (Mean)** | ~6.49 ms          | **~5.88 ms**     | **~9.4% Faster**  |
| **Sync Throughput (Mean)**  | ~18.29 ms         | **~16.82 ms**    | **~8.0% Faster**  |

*Note: Benchmarks measure network-isolated internal overhead. Routing operations per second (OPS) jumped from ~55k to over **718k**.*

______________________________________________________________________

## Profiling the Codebase

If you modify core internal logic, verify that you have not introduced I/O regressions or memory leaks.

**To profile Cold-Boot initialization:**

```bash
python tests/test_boot.py
```

**To benchmark the routing and throughput performance**

```bash
pytest tests/test_perf.py --benchmark-compare
```
