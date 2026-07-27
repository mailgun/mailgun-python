# Mailgun Python SDK: Performance & Architecture

This document outlines the architectural decisions made to ensure the Mailgun Python SDK remains blazingly fast, memory-efficient, and secure.

If you are contributing to this repository, please review these principles before modifying core routing, transport, or instantiation logic.

## Core Optimizations

### 1. Constant-Time (O(1)) Dictionary Dispatch (`routes.py`)

String manipulation, dynamic imports (`importlib`), and sequential regex evaluations are historically slow in Python.

- **Static Dispatch:** Base API URLs and handler functions are pre-mapped in immutable dictionaries (`EXACT_ROUTES`, `PREFIX_ROUTES`).
- **Impact:** The SDK completely avoids string concatenation and dynamic resolution during high-volume request loops, sustaining over **1 million routing operations per second**.

### 2. High-Concurrency Transport Layer (`httpx` & `__slots__`)

- **Native AsyncIO & Connection Pooling:** The `AsyncClient` allows for true non-blocking throughput. Both clients enforce connection pooling to prevent OS socket exhaustion.
- **Memory Density (`__slots__`):** By defining `__slots__` on `Endpoint` and `Client` classes, we block Python from creating dynamic `__dict__` hash tables, minimizing RAM footprint and garbage collection pauses.

### 3. Streamlined Cold-Boot Initialization

- **Optimized Import Paths:** By reducing unnecessary module imports and lazy-loading heavy components, the initialization sequence executes **~45,000 fewer function calls** than baseline versions.
- **Impact:** Speeds up cold starts, making the SDK exceptionally well-suited for serverless environments (AWS Lambda, Google Cloud Functions).

### 4. Zero-Regression Security Guardrails

- Core request preparation incorporates `SecurityGuard`, `IdempotencyGuard`, and `RetryPolicy` with virtually zero performance penalty (~78 ns security tax on routing). We intentionally trade these microscopic CPU cycles to provide enterprise-grade safety.

______________________________________________________________________

## Benchmarks (v1.8.0 vs. v1.9.0)

| Metric                      | v1.8.0 (Baseline) | v1.9.0 (Current) | Delta / Notes                          |
| :-------------------------- | :---------------- | :--------------- | :------------------------------------- |
| **Cold Boot Time**          | ~0.316 s          | **~0.230 s**     | **~27.2% Faster** (Optimized imports)  |
| **Routing Speed (Mean)**    | ~0.84 µs          | **~0.92 µs**     | **+78 ns** (Security validation tax)   |
| **Async Throughput (Mean)** | ~3.72 ms          | **~3.68 ms**     | **Stable** (Parity)                    |
| **Sync Throughput (Mean)**  | ~9.84 ms          | **~10.39 ms**    | **+0.55 ms** (Thread coordination tax) |

*Note: Tests were executed on CPython 3.13 (Apple M4 Pro, Darwin ARM64-bit) in an isolated environment.*

______________________________________________________________________

## Benchmarks (v1.7.0 vs. v1.8.0)

This suite proves that the introduction of enterprise-grade security layers (`SecurityGuard`, strict payload schemas) introduced virtually **zero performance regressions** in the active hot path.

| Metric                      | v1.7.0 (Baseline) | v1.8.0 (Current) | Delta / Notes                           |
| :-------------------------- | :---------------- | :--------------- | :-------------------------------------- |
| **Cold Boot Time**          | ~0.130 s          | **~0.126 s**     | **~3.0% Faster**                        |
| **Routing Speed (Mean)**    | ~1.22 µs          | **~1.20 µs**     | **Flat** (Statistical noise)            |
| **Async Throughput (Mean)** | **~0.11 ms**\*    | ~15.76 ms        | **Fixed Pipeline** (See note)           |
| **Sync Throughput (Mean)**  | **~0.25 ms**      | ~0.28 ms         | **+ 0.03 ms** (Security validation tax) |

*\* The v1.7.0 Async Throughput time reflects a deprecated test state where the mock transport was accidentally bypassed, resulting in an instant loop crash rather than a full HTTP pipeline execution. The v1.8.0 metric reflects the true, successfully mocked execution.*

______________________________________________________________________

## Benchmarks (v1.6.0 vs. v1.7.0)

Our internal `pytest-benchmark` and `cProfile` suites verify these architectural gains. Tests were executed on CPython 3.13 (Darwin 64-bit).

| Metric                      | v1.6.0 (Baseline) | v1.7.0 (Current) | Delta             |
| :-------------------------- | :---------------- | :--------------- | :---------------- |
| **Cold Boot Time**          | ~0.232 s          | **~0.201 s**     | **~13% Faster**   |
| **Routing Speed (Mean)**    | ~17.98 µs         | **~1.39 µs**     | **~12.9x Faster** |
| **Async Throughput (Mean)** | ~6.49 ms          | **~5.88 ms**\*   | **~9.4% Faster**  |
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
