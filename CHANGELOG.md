# CHANGELOG

We [keep a changelog.](http://keepachangelog.com/)

## [Unreleased]

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

- Breaking changes! It's a new Python SKD for [Mailgun](http://www.mailgun.com/); an obsolete v0.1.1 on [PyPI](https://pypi.org/project/mailgun/0.1.1/) is deprecated.

### Pull Requests Merged

- [PR_2](https://github.com/mailgun/mailgun-python/pull/2) - Improve and update API versioning
- [PR_4](https://github.com/mailgun/mailgun-python/pull/4) - Update README.md
- [PR_6](https://github.com/mailgun/mailgun-python/pull/6) - Release v1.0.0
- [PR_7](https://github.com/mailgun/mailgun-python/pull/7) - Add issue templates

[1.0.0]: https://github.com/mailgun/mailgun-python/releases/tag/v1.0.0
[1.0.1]: https://github.com/mailgun/mailgun-python/releases/tag/v1.0.1
[1.0.2]: https://github.com/mailgun/mailgun-python/releases/tag/v1.0.2
[1.1.0]: https://github.com/mailgun/mailgun-python/releases/tag/v1.1.0
[unreleased]: https://github.com/mailgun/mailgun-python/releases/tag/v1.1.0...HEAD
