# CHANGELOG

We [keep a changelog.](http://keepachangelog.com/)

## [Unreleased]

## [1.7.0] - 2026-05-01

### Added

- Explicit `__all__` declaration in `mailgun.client` to cleanly isolate the public API namespace.
- A `__repr__` method to the `Client` and `BaseEndpoint` classes to improve developer experience (DX) during console debugging (showing target routes instead of memory addresses).
- Security guardrail (CWE-319) in `Config` that logs a warning if a cleartext `http://` API URL is configured.
- Python 3.14 support to the GitHub Actions test matrix.
- Implemented Smart Logging (telemetry) in `Client` and `AsyncClient` to help users debug API requests, generated URLs, and server errors (`404`, `400`, `429`).
- Smart Webhook Routing: Implemented payload-based routing for domain webhooks. The SDK dynamically routes to `v1`, `v3`, or `v4` endpoints based on the HTTP method and presence of parameters like `event_types` or `url`.
- Deprecation Interceptor: Added a registry and interception hook that emits non-breaking `DeprecationWarning`s and logs when utilizing obsolete Mailgun APIs (e.g., v3 validations, legacy tags, v1 bounce-classification).
- Added `build_path_from_keys` utility in `mailgun.handlers.utils` to centralize and dry up URL path generation across handlers.
- Overrode __dir__ in Client and AsyncClient to expose dynamic endpoint routes (e.g., .messages, .domains) directly to IDE autocompletion engines (VS Code, PyCharm).
- Native dynamic routing support for Mailgun Optimize, Validations Service, and Email Preview APIs without requiring new custom handlers.
- Explicit support for raw MIME string (`multipart/form-data`) uploads via the `files` parameter in the `.create()` method (essential for `client.mimemessage`).
- Advanced path interpolation in `handle_default` to automatically inject inline URL parameters (e.g., `/v2/x509/{domain}/status`).
- Added `MailgunTimeoutError` (inheriting from `ApiError` and `TimeoutError`) to cleanly distinguish API connection timeouts from standard system timeouts.
- Implemented `ROUTE_ALIASES` in the configuration engine to safely route virtual SDK properties (e.g., `domains_webhooks`) without hardcoding intercept logic.
- Added `TimeoutType` type alias for cleaner and more robust type hinting across the HTTP client.
- Added a new "Logging & Debugging" section to `README.md`.
- An intelligent live meta-testing suite (`test_routing_meta_live.py`) to strictly verify SDK endpoint aliases against live Mailgun servers.
- PEP 561 Compliance: Added a `py.typed` marker to expose the SDK's strict type hints to downstream users (`mypy`, `pyright`).
- DX Tooling: Added a unified `manage.sh` script to streamline local formatting, linting, testing, and benchmarking.
- Routing Engine Meta-Tests: Added `test_routing_engine.py` to dynamically validate URL generation for all 58+ supported endpoints.

### Changed

- **Memory Optimization:** Enforced `__slots__` on `Client` and `Endpoint` classes to eliminate dynamic `__dict__` overhead, reducing Garbage Collection pauses and improving overall throughput by ~8-10%.
- Exception Chaining (PEP 3134): Network connection errors from `httpx` and `requests` are now explicitly chained (`raise from`), preventing the swallowing of root-cause infrastructure tracebacks.
- Refactored the `Config` routing engine to use a deterministic, data-driven approach (`EXACT_ROUTES` and `PREFIX_ROUTES`) for better maintainability.
- Improved dynamic API version resolution for domain endpoints to gracefully switch between `v1`, `v3`, and `v4` for nested resources, with a safe fallback to `v3`.
- Secured internal configuration registries by wrapping them in `MappingProxyType` to prevent accidental mutations of the client state.
- Broadened type hints for `files` (`Any | None`) and `timeout` (`int | float | tuple`) to fully support `requests`/`httpx` capabilities (like multipart lists) without triggering false positives in strict IDEs.
- **Performance**: Implemented automated Payload Minification. The SDK now strips structural spaces from JSON payloads (`separators=(',', ':')`), reducing network overhead by ~15-20% for large batch requests.
- **Performance**: Memoized internal route resolution logic using `@lru_cache` in `_get_cached_route_data`, eliminating redundant string splitting and dictionary lookups during repeated API calls.
- Updated `DOMAIN_ENDPOINTS` mapping to reflect Mailgun's latest architecture, officially moving `tracking`, `click`, `open`, `unsubscribe`, and `webhooks` from `v1` to `v3`.
- Modernized the codebase using modern Python idioms (e.g., `contextlib.suppress`) and resolved strict typing errors for `pyright`.
- Abstracted HTTP header manipulation into a centralized `_merge_headers` method in `BaseEndpoint`, eliminating DRY violations across all sync and async HTTP verbs.
- Hardened all URL handlers (`domains`, `ips`, `keys`, `mailinglists`, `metrics`, `routes`, `suppressions`, `tags`) to use `.rstrip("/")` and safe `.get("keys", [])` dictionary lookups, preventing `404 Not Found` and `KeyError` crashes from malformed internal configurations.
- Replaced `pass` blocks with explicit `logging.warning` in integration tests to surface ignored 404s gracefully.
- **Documentation**: Migrated all internal and public docstrings from legacy Sphinx/reST format to modern Google Style for cleaner readability and better IDE hover-hints.
- Updated Dependabot configuration to group minor and patch updates and limit open PRs.
- CI/CD Optimization: Grouped Dependabot updates (`minor-and-patch`) to reduce Pull Request noise and optimized `.editorconfig`.
- Migrated the fragmented linting and formatting pipeline (Flake8, Black, Pylint, Pyupgrade, etc.) to a unified, high-performance `ruff` setup in `.pre-commit-config.yaml`.
- Refactored `api_call` exception blocks to use the `else` clause for successful returns, adhering to strict Ruff (TRY300) standards.
- Enabled pip dependency caching in GitHub Actions to drastically speed up CI workflows.
- Fixed API versioning collisions in `DOMAIN_ENDPOINTS` (e.g., ensuring `tracking` correctly resolves to `v3` instead of `v1`).
- Corrected the `credentials` route prefix to properly inject the `domains/` path segment.
- Updated `README.md` with new documentation, IDE DX features, and code examples for Validations & Optimize APIs.
- Cleaned up obsolete unit tests that conflicted with the new forgiving dynamic Catch-All routing architecture.

### Fixed

- Fixed a silent data loss bug in `create()` where custom `headers` passed by the user were ignored instead of being merged into the request.
- Fixed a kwargs collision bug in `update()` by using `.pop("headers")` instead of `.get()` to prevent passing duplicate keyword arguments to the underlying request.
- Preserved original tracebacks (PEP 3134) by properly chaining `TimeoutError` and `ApiError` using `from e`.
- Used safely truncating massive HTML error responses to 500 characters (preventing a log-flooding vulnerability (OWASP CWE-532)).
- Replaced a fragile `try/except TypeError` status code check with robust `getattr` and `isinstance` validation to prevent masking unrelated exceptions.
- Resolved `httpx` `DeprecationWarning` in `AsyncEndpoint` by properly routing serialized JSON string payloads to the `content` parameter instead of `data`.
- Fixed a bug in `domains_handler` where intermediate path segments were sometimes dropped for nested resources like `/credentials` or `/ips`.
- Fixed flaky integration tests failing with `429 Too Many Requests` and `403 Limits Exceeded` by adding proper eventual consistency delays and state teardowns.
- Fixed DKIM key generation tests to use the `-traditional` OpenSSL flag, ensuring valid PKCS1 format compatibility.
- Fixed DKIM selector test names to strictly comply with RFC 6376 formatting (replaced underscores with hyphens).
- Python Data Model Integrity: The Catch-All router (`__getattr__`) now strictly rejects Python magic methods (`__dunder__`), preventing crashes when using `hasattr()`, `pickle`, or `copy.deepcopy()`.
- Version Drift: Corrected endpoints for `spamtraps` and `ip_whitelist` to route to their modern `v2` Mailgun backends.
- Fixed a `TypeError: got multiple values for keyword argument 'headers'` crash when passing custom headers to `.get()`, `.put()`, `.patch()`, and `.delete()` methods by safely popping headers from `kwargs` before argument unpacking.
- Fixed a routing bug where the greedy `domains` router swallowed the `domains_webhooks` identifier, causing webhook payload updates to drop the `webhook_name` and hit the wrong API endpoint.
- Fixed a bug where `AsyncClient` transports were permanently closed after exiting an `async with` context manager, allowing safe client reuse across multiple blocks.
- Fixed `AttributeError` traceback leakage by strictly suppressing internal `KeyError`s from the dynamic router (`raise ... from None`).
- Fixed a silent string-concatenation bug that could generate invalid double-slashes (`//`) in base URLs during the `Config` engine initialization.
- Fixed `email_validation_examples.py` to correctly `raise` the `ValueError` on empty files instead of failing silently.

### Security

- OWASP Credential Protection: Implemented a `SecretAuth` tuple subclass to securely redact the Mailgun API key from accidental exposure in memory dumps, tracebacks, and `repr()` logs.
- OWASP Input Validation: Added strict sanitization in `Client._validate_auth` to strip trailing whitespace and block HTTP Header Injection attacks (rejecting `\n` and `\r` characters in API keys).
- CWE-113 (HTTP Header Injection): Implemented strict CRLF (`\r\n`) sanitization inside `SecurityGuard.sanitize_headers` to block malicious header manipulation.
- Supply Chain Security: Patched a potential OS Command Injection vulnerability in GitHub Actions (`publish.yml`) by safely routing `github.*` contexts through environment variables.
- CWE-22 (Path Traversal): Enforced strict URL-encoding via `sanitize_path_segment` on `webhook_name` parameters to neutralize path traversal injection attempts in the `handle_webhooks` router.

### Pull Requests Merged

- [PR_39](https://github.com/mailgun/mailgun-python/pull/39) - Release 1.7.0
- [PR_38](https://github.com/mailgun/mailgun-python/pull/38) - build(deps): Bump conda-incubator/setup-miniconda from 3.3.0 to 4.0.1
- [PR_36](https://github.com/mailgun/mailgun-python/pull/36) - Improve client, update & fix tests
- [PR_35](https://github.com/mailgun/mailgun-python/pull/35) - Removed \_prepare_files logic
- [PR_34](https://github.com/mailgun/mailgun-python/pull/34) - Improve the Config class and routes
- [PR_33](https://github.com/mailgun/mailgun-python/pull/32) - Refactored test framework
- [PR_31](https://github.com/mailgun/mailgun-python/pull/31) - Add missing py.typed in module directory
- [PR_30](https://github.com/mailgun/mailgun-python/pull/30) - build(deps): Bump conda-incubator/setup-miniconda from 3.2.0 to 3.3.0

## [1.6.0] - 2026-01-08

### Added

- Add Keys and Domain Keys API endpoints:

  - Add `handle_keys` to `mailgun.handlers.keys_handler`.
  - Add `handle_dkimkeys` to `mailgun.handlers.domains_handler`.
  - Add "dkim" key to special cases in the class `Config`.

- Examples:

  - Add the `get_dkim_keys()`, `post_dkim_keys()`, `delete_dkim_keys()` examples to `mailgun/examples/domain_examples.py`.
  - Add the `get_keys()`, `post_keys()`, `delete_key()`, `regenerate_key()` examples to `mailgun/examples/keys_examples.py`.

- Docs:

  - Add `Keys` and `Domain Keys` sections with examples to `README.md`.
  - Add docstrings to the test class `KeysTests` & `AsyncKeysTests` and their methods.
  - Add `CONTRIBUTING.md`.
  - Add `MANIFEST.in`.

- Tests:

  - Add dkim keys tests to `DomainTests` and only `test_get_dkim_keys`, `test_post_dkim_keys_invalid_pem_string` to `AsyncDomainTests`.
  - Add classes `KeysTests` and `AsyncKeysTests` to `tests/tests.py`.
  - Add keys tests to `KeysTests` and `AsyncKeysTests`.

- CI:

  - Add more pre-commit hooks.

### Changed

- Update `get_own_user_details()` by creating `client_with_secret_key` in `mailgun/examples/users_examples.py`.
- Improve the users' example in `README.md`.
- Fix markdown structure in `README.md`.
- Update environment variables in `README.md`.
- Move `BounceClassificationTests` to another place in `tests/tests.py`.
- Replace some pytest's skip marks with xfail.
- Disable `codespell` pre-commit hook as it lashes with `typos`.
- Update `pre-commit` hooks to the latest versions.
- Update test dependencies: add `openssl` and `pytest-asyncio` to `environment-dev.yaml` and `pyproject.toml`.
- Add `.server.key` to `.gitignore`.
- Add a constraint `py<311` for `typing_extensions >=4.7.1` in files `environment.yaml`, `environment-dev.yaml`, `pyproject.toml`, and in `mailgun/client.py`.
- Improve `pyproject.toml`.

### Pull Requests Merged

- [PR_27](https://github.com/mailgun/mailgun-python/pull/27) - Add Keys and Domain Keys API endpoints
- [PR_29](https://github.com/mailgun/mailgun-python/pull/29) - Release v1.6.0

## [1.5.0] - 2025-12-11

### Added

- Add `AsyncClient` and `AsyncEndpoint` that work based on asynchronous approach. Signatures and usage is basically the same but `AsyncClient`
  supports async context manager mode.

- Add `httpx >=0.24.0` as an additional runtime dependency in order to support async/await and also `typing_extensions >=4.7.1` to `environment.yaml`, `environment-dev.yaml`, and `pyproject.toml`.

- Add missing endpoints:

  - Add `"users"`, `"me"` to the `users` key of special cases in the class `Config`.
  - Add `handle_users` to `mailgun.handlers.users_handler` for parsing [Users API](https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/users).
  - Add `handle_mailboxes_credentials()` to `mailgun.handlers.domains_handler` for parsing `Update Mailgun SMTP credentials` in [Credentials API](https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/credentials).

- Examples:

  - Add async examples to `async_client_examples.py`.
  - Move credentials examples from `mailgun/examples/domain_examples.py` to `mailgun/examples/credentials_examples.py` and add a new example `put_mailboxes_credentials()`.
  - Add the `get_routes_match()` example to `mailgun/examples/routes_examples.py`.
  - Add the `update_template_version_copy()` example to `mailgun/examples/templates_examples.py`.
  - Add `mailgun/examples/users_examples.py`.

- Docs:

  - Add the `AsyncClient` section to `README.md`.
  - Add `Credentials` and `Users` sections with examples to `README.md`.
  - Add docstrings to the test class `UsersTests` & `AsyncUsersTests` and theirs methods.

- Tests:

  - Add same tests for `AsyncClient` as exist for `Client`.
  - Add `test_put_mailboxes_credentials` to `DomainTests` and `AsyncDomainTests`.
  - Add `test_get_routes_match` to `RoutesTests` and `AsyncRoutesTests`.
  - Add `test_update_template_version_copy` to `TemplatesTests ` and `AsyncTemplatesTests`.
  - Add classes `UsersTests` and `AsyncUsersTests` to `tests/tests.py`.

### Changed

- Update `handle_templates()` in `mailgun/handlers/templates_handler.py` to handle `new_tag`.
- Update CI workflows: update `pre-commit` hooks to the latest versions.
- Modify `mypy`'s additional_dependencies in `.pre-commit-config.yaml` to suppress `error: Untyped decorator makes function` by adding `pytest-order`.
- Replace spaces with tabs in `Makefile`.
- Update `Makefile`: add `make check-env` and improve `make test`.

### Pull Requests Merged

- [PR_24](https://github.com/mailgun/mailgun-python/pull/24) - Async client support
- [PR_25](https://github.com/mailgun/mailgun-python/pull/25) - Add missing endpoints
- [PR_26](https://github.com/mailgun/mailgun-python/pull/26) - Release v1.5.0

## [1.4.0] - 2025-11-20

### Added

- Add the `Bounce Classification` endpoint:
  - Add `bounce-classification`, `metrics` to the `bounceclassification` key of special cases in the class `Config`.
  - Add `bounce_classification_handler.py` to parse Bounce Classification API.
  - Add `mailgun/examples/bounce_classification_examples.py` with `post_list_statistic_v2()`.
  - Add `Bounce Classification` sections with an example to `README.md`.
  - Add class `BounceClassificationTests ` to `tests/tests.py`.
  - Add docstrings to the test class `BounceClassificationTests` and its methods.

### Changed

- Fix `Metrics`, `Tags New` & `Logs` docstrings in tests.
- Update CI workflows: update `pre-commit` hooks to the latest versions.
- Apply linters: remove redundant `type: ignore`.

### Pull Requests Merged

- [PR_22](https://github.com/mailgun/mailgun-python/pull/22) - Add support for the Bounce Classification v2 API
- [PR_23](https://github.com/mailgun/mailgun-python/pull/23) - Release v1.4.0

## [1.3.0] - 2025-11-08

### Added

- Add the `Tags New` endpoint:
  - Add `tags` to the `analytics` key of special cases in the class `Endpoint`.
  - Add `mailgun/examples/tags_new_examples.py` with `post_analytics_tags()`, `update_analytics_tags()`, `delete_analytics_tags()`, `get_account_analytics_tag_limit_information()`.
  - Add `Tags New` sections with examples to `README.md`.
  - Add class `TagsNewTests` to tests/tests.py.
- Add `# pragma: allowlist secret` for pseudo-passwords.
- Add the `pytest-order` package to `pyproject.toml`'s test dependencies and to `environment-dev.yaml` for ordering some `DomainTests`, `Messages` and `TagsNewTests`.
- Add docstrings to the test classes.
- Add Python 3.14 support.

### Changed

- Update `metrics_handler.py` to parse Tags New API.
- Mark deprecated `Tags API` in `README.md` with a warning.
- Fix `Metrics` & `Logs` docstrings.
- Format `README.md`.
- Use ordering for some tests by adding `@pytest.mark.order(N)` to run specific tests sequentionally. It allows to remove some unnecessary `@pytest.mark.skip()`
- Rename some test classes, e.i., `ComplaintsTest` -> `ComplaintsTests` for consistency.
- Use `datetime` for `LogsTests` data instead of static date strings.
- Update CI workflows: update `pre-commit` hooks to the latest versions; add py314 support (limited).
- Set `line-length` to `100` across the linters in `pyproject.toml`.

### Pull Requests Merged

- [PR_20](https://github.com/mailgun/mailgun-python/pull/20) - Add support for the Tags New API endpoint
- [PR_21](https://github.com/mailgun/mailgun-python/pull/21) - Release v1.3.0

## [1.2.0] - 2025-10-02

### Added

- Add the Logs endpoint:
  - Add `logs` to the `analytics` key of special cases
  - Add `mailgun/examples/logs_examples.py` with `post_analytics_logs()`
  - Add class `LogsTest` to tests/tests.py
  - Add `Get account logs` sections with an example to `README.md`
  - Add class `LogsTest` to tests/tests.py
- Add `black` to `darker`'s additional_dependencies in `.pre-commit-config.yaml`
- Add docstrings to the test classes.

### Changed

- Update pre-commit hooks to the latest versions
- Fix indentation of the `post_bounces()` example in `README.md`
- Fix some pylint warnings related to docstrings
- Update CI workflows

### Pull Requests Merged

- [PR_18](https://github.com/mailgun/mailgun-python/pull/18) - Add support for the Logs API endpoint
- [PR_19](https://github.com/mailgun/mailgun-python/pull/19) - Release v1.2.0

## [1.1.0] - 2025-07-12

### Added

- Add the Metrics endpoint:
  - Add the `analytics` key to `Config`'s `__getitem__` and special cases
  - Add `mailgun/handlers/metrics_handler.py` with `handle_metrics()`
  - Add `mailgun/examples/metrics_examples.py` with `post_analytics_metrics()` and `post_analytics_usage_metrics()`
  - Add class `MetricsTest` to tests/tests.py
  - Add `Get account metrics` and `Get account usage metrics` sections with examples to `README.md`
- Add `pydocstyle` pre-commit hook
- Add `types-requests` to `mypy`'s additional_dependencies

### Changed

- Breaking changes: drop support for Python 3.9
- Improve a conda recipe
- Enable `refurb` in `environment-dev.yaml`
- Use `project.license` and `project.license-files` in `pyproject.toml` because of relying on `setuptools >=77`.
- Update pre-commit hooks to the latest versions
- Fix type hints in `mailgun/handlers/domains_handler.py` and `mailgun/handlers/ip_pools_handler.py`
- Update dependency pinning in `README.md`

### Removed

- Remove `_version.py` from tracking and add to `.gitignore`
- Remove the `wheel` build dependency

### Pull Requests Merged

- [PR_14](https://github.com/mailgun/mailgun-python/pull/14) - Add support for Metrics endpoint
- [PR_16](https://github.com/mailgun/mailgun-python/pull/16) - Release v1.1.0

## [1.0.2] - 2025-06-24

### Changed

- docs: Minor clean up in README.md
- ci: Update pre-commit hooks to the latest versions

### Security

- docs: Add the Security Policy file SECURITY.md
- ci: Use permissions: contents: read in all CI workflow files explicitly
- ci: Use commit hashes to ensure reproducible builds
- build: Update dependency pinning: requests>=2.32.4

### Pull Requests Merged

- [PR_13](https://github.com/mailgun/mailgun-python/pull/13) - Release v1.0.2: Improve CI workflows & packaging

## [1.0.1] - 2025-05-27

### Changed

- docs: Fixed package name in README.md

### Pull Requests Merged

- [PR_11](https://github.com/mailgun/mailgun-python/pull/11) - Fix package name

## [1.0.0] - 2025-04-22

### Added

- Initial release

### Changed

- Breaking changes! It's a new Python SKD for [Mailgun](http://www.mailgun.com/); an obsolete v0.1.1 on
  [PyPI](https://pypi.org/project/mailgun/0.1.1/) is deprecated.

### Pull Requests Merged

- [PR_2](https://github.com/mailgun/mailgun-python/pull/2) - Improve and update API versioning
- [PR_4](https://github.com/mailgun/mailgun-python/pull/4) - Update README.md
- [PR_6](https://github.com/mailgun/mailgun-python/pull/6) - Release v1.0.0
- [PR_7](https://github.com/mailgun/mailgun-python/pull/7) - Add issue templates

[1.0.0]: https://github.com/mailgun/mailgun-python/releases/tag/v1.0.0
[1.0.1]: https://github.com/mailgun/mailgun-python/releases/tag/v1.0.1
[1.0.2]: https://github.com/mailgun/mailgun-python/releases/tag/v1.0.2
[1.1.0]: https://github.com/mailgun/mailgun-python/releases/tag/v1.1.0
[1.2.0]: https://github.com/mailgun/mailgun-python/releases/tag/v1.2.0
[1.3.0]: https://github.com/mailgun/mailgun-python/releases/tag/v1.3.0
[1.4.0]: https://github.com/mailgun/mailgun-python/releases/tag/v1.4.0
[1.5.0]: https://github.com/mailgun/mailgun-python/releases/tag/v1.5.0
[1.6.0]: https://github.com/mailgun/mailgun-python/releases/tag/v1.6.0
[unreleased]: https://github.com/mailgun/mailgun-python/compare/v1.6.0...HEAD
