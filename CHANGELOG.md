# CHANGELOG

We [keep a changelog.](http://keepachangelog.com/)

## [Unreleased]

## [1.3.0] - 2025-11-08

### Added

- Add the `Tags New` endpoint:
  - Add `tags` to the `analytics` key of special cases in the class `Endpoint`.
  - Add `mailgun/examples/tags_new_examples.py` with `post_analytics_tags()`, `update_analytics_tags()`, `delete_analytics_tags()`, `get_account_analytics_tag_limit_information()`.
  - Add `Tags New` sections with examples to `README.md`.
  - Add docstrings to the test classes.
  - Add class `TagsNewTests` to tests/tests.py.
  - Add `# pragma: allowlist secret` for pseudo-passwords.
  - Add the `pytest-order` package to `pyproject.toml`'s test dependencies and to `environment-dev.yaml` for ordering some `DomainTests`, `Messages` and `TagsNewTests`.
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
[unreleased]: https://github.com/mailgun/mailgun-python/compare/v1.1.0...HEAD
