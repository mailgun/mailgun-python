# CHANGELOG

We [keep a changelog.](http://keepachangelog.com/)

## [Unreleased]

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
[unreleased]: https://github.com/mailgun/mailgun-python/compare/v1.5.0...HEAD
