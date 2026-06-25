import math
import re
import ssl
import sys
import unicodedata
import warnings
from pathlib import Path
from typing import Any, Final
from urllib.parse import quote, unquote, urlparse

from requests.adapters import HTTPAdapter

from mailgun.logger import get_logger
from mailgun.types import TimeoutType


logger = get_logger(__name__)

# Constants for API error handling and logging (fixes Ruff PLR2004)
_AUTH_TUPLE_LEN: Final = 2
# Regex to detect any ASCII control character EXCEPT horizontal tab (\x09)
# Compliant with RFC 9110 Section 5.5
_CONTROL_CHAR_RE: Final = re.compile(r"[\x00-\x08\x0a-\x1f\x7f]")

_PATH_CONTROL_CHAR_RE: Final = re.compile(r"[\x00-\x1f\x7f]")
_XSS_PATTERN: Final = re.compile(r"<(script|svg)|javascript:|onload=", re.IGNORECASE)

ALLOWED_HOSTS: Final = frozenset(
    {"mailgun.net", "mailgun.org", "mailgun.com", "localhost", "127.0.0.1"}
)
ALLOWED_SUFFIXES: Final = (".mailgun.net", ".mailgun.org", ".mailgun.com")
ALLOWED_SCHEMES: Final = frozenset({"https", "http"})


class SecureHTTPAdapter(HTTPAdapter):
    """Enforce Minimum TLS 1.2+ Protocol Context (MITM & Downgrade Prevention).

    Mitigates CWE-319.
    """

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the pool manager with a secure TLS context."""
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = context
        # HTTPAdapter lacks strict static types for this internal method.
        super().init_poolmanager(*args, **kwargs)


class SecretAuth(tuple):  # type: ignore[type-arg]
    """OWASP: Obfuscate credentials in memory dumps and tracebacks."""

    __slots__ = ()  # DX & Performance: Prevent __dict__ creation to optimize memory usage.

    def __repr__(self) -> str:
        """Return a safe representation of the credential."""
        return "('api', '***REDACTED***')"


class SecurityGuard:
    """Centralized security validation and sanitization (Defense in Depth).

    This class isolates all Zero-Trust guardrails, enforcing SRP and making it
    easy to extract into a dedicated security module in future releases.
    """

    ALLOWED_HTTP_METHODS: Final[frozenset[str]] = frozenset(
        {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}
    )
    ALLOWED_API_HOSTS: Final[tuple[str, ...]] = (
        "mailgun.net",
        "mailgun.org",
        "localhost",
        "127.0.0.1",
    )
    ALLOWED_KWARGS: Final[frozenset[str]] = frozenset({"proxies", "cert"})
    SAFE_KEY_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9_]+$")
    CRLF_SLASH_PATTERN: Final[re.Pattern[str]] = re.compile(r"[\r\n/\\]+")

    @classmethod
    def sanitize_api_url(cls, raw_url: str) -> str:
        """Sanitize and validate the base API URL to prevent SSRF and Cleartext transmission.

        Args:
            raw_url: The raw URL string to sanitize.

        Returns:
            The sanitized URL string without a trailing slash.

        Raises:
            ValueError: If the URL uses prohibited cleartext HTTP (CWE-319).
        """
        raw_url = raw_url.strip().replace("\r", "").replace("\n", "")
        parsed = urlparse(raw_url)

        if not parsed.scheme:
            raw_url = f"https://{raw_url}"
            parsed = urlparse(raw_url)

        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"}:
            msg = (
                "CRITICAL SECURITY: Cleartext HTTP transmission is prohibited (CWE-319). Use HTTPS."
            )
            raise ValueError(msg)  # Fail Closed

        hostname = parsed.hostname or ""
        is_valid_host = any(
            hostname == allowed or hostname.endswith(f".{allowed}")
            for allowed in cls.ALLOWED_API_HOSTS
        )
        if not is_valid_host:
            msg = (
                f"SECURITY WARNING: Invalid API host '{hostname}'. Ensure this is a trusted proxy."
            )
            logger.warning(msg)

        return raw_url.rstrip("/")

    @classmethod
    def validate_auth(cls, auth: tuple[str, str] | None) -> tuple[str, str] | None:
        """Sanitize and validate credentials against Header Injection vulnerabilities.

        Args:
            auth: A tuple containing the API user and API key, or None.

        Returns:
            A SecretAuth tuple with cleaned credentials, or None if no auth was provided.

        Raises:
            ValueError: If the API key contains invalid characters (e.g., newlines).
        """
        if auth and isinstance(auth, tuple) and len(auth) == _AUTH_TUPLE_LEN:
            clean_user = str(auth[0]).strip()
            clean_key = str(auth[1]).strip()

            if "\n" in clean_key or "\r" in clean_key:
                raise ValueError("API Key contains invalid characters (Header Injection risk).")

            return SecretAuth((clean_user, clean_key))
        return auth

    @classmethod
    def sanitize_key(cls, key: str) -> str:
        """Normalize and validate the endpoint key from IDE Introspection.

        Args:
            key: The raw endpoint key to sanitize.

        Returns:
            The sanitized and validated endpoint key.

        Raises:
            KeyError: If the resulting key is invalid or empty.
        """
        clean_key: str = key.lower()
        if not cls.SAFE_KEY_PATTERN.fullmatch(clean_key):
            clean_key = re.sub(r"[^a-z0-9_]", "", clean_key)
        if not clean_key:
            msg = f"Invalid endpoint key: {key}"
            raise KeyError(msg)
        return clean_key

    @classmethod
    def sanitize_domain(cls, domain: str | None) -> str | None:
        """Protect against Path Traversal in URL construction.

        Args:
            domain: Target domain name to sanitize.

        Returns:
            The sanitized domain name or None.

        Raises:
            ValueError: If path traversal characters are detected.
        """
        if not domain:
            return None

        decoded_domain = unquote(domain)

        # Poka-yoke: Actively strip all slashes and newlines (Advanced Traversal & CRLF)
        safe_domain = cls.CRLF_SLASH_PATTERN.sub("", decoded_domain).strip()

        if ".." in safe_domain:
            raise ValueError(
                "CRITICAL SECURITY: Path traversal characters detected in domain parameter."
            )
        return safe_domain

    @classmethod
    def sanitize_http_method(cls, method: str) -> str:
        """Prevent HTTP Verb Tampering and Attribute Injection.

        Args:
            method: The HTTP method requested.

        Returns:
            A safely formatted HTTP method string.

        Raises:
            ValueError: If the method is not in the allowed list.
        """
        safe_method = str(method).strip().upper()
        if safe_method not in cls.ALLOWED_HTTP_METHODS:
            msg = f"CRITICAL SECURITY: HTTP method '{safe_method}' is prohibited."
            raise ValueError(msg)
        return safe_method

    @classmethod
    def sanitize_timeout(cls, timeout: TimeoutType) -> TimeoutType:
        """Prevent Infinite Timeout Thread Exhaustion (DoS).

        Strict Creation-Time Timeout Constraints & Float Validation.
        Prevents thread pool exhaustion from infinite blocking (CWE-400).

        Args:
            timeout: The requested timeout value.

        Returns:
            The safely verified timeout value.

        Raises:
            ValueError: If the timeout is a negative number, zero, non-finite,
                or a tuple with an incorrect number of elements.
        """
        if timeout is None:
            # Soft Deprecation
            warnings.warn(
                "Passing 'timeout=None' allows infinite socket blocking (CWE-400). "
                "This will be removed in a future major release. Please provide an explicit timeout.",
                DeprecationWarning,
                stacklevel=3,
            )
            return None

        def _validate_float(val: Any) -> float:
            """Validate float value.

            Args:
                val: The timeout value.

            Returns:
                The timeout float value.

            Raises:
                TypeError: If the timeout is not a numeric type.
                ValueError: If the timeout is NaN, Infinity, or less than or equal to zero.
            """
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                msg = f"Timeout must be a numeric value, got {type(val).__name__}"
                raise TypeError(msg)

            f_val = float(val)

            if math.isnan(f_val) or math.isinf(f_val):
                raise ValueError("Timeout must be a finite number.")
            if f_val <= 0:
                raise ValueError("Timeout must be a strictly positive finite number.")
            return f_val

        if isinstance(timeout, tuple):
            expected_tuple_length = 2
            if len(timeout) != expected_tuple_length:
                raise ValueError(
                    "Timeout must be a tuple containing exactly two elements: (connect, read)."
                )
            return (_validate_float(timeout[0]), _validate_float(timeout[1]))

        return _validate_float(timeout)

    @classmethod
    def filter_safe_kwargs(cls, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Prevent Mass Assignment of internal HTTP client states.

        Args:
            kwargs: Dictionary of keyword arguments passed to the network layer.

        Returns:
            A filtered dictionary containing only allowed low-level HTTP settings.
        """
        return {k: v for k, v in kwargs.items() if k in cls.ALLOWED_KWARGS}

    @staticmethod
    def sanitize_headers(headers: dict[str, str] | None) -> dict[str, str] | None:
        """Poka-yoke: Prevent HTTP Header Injection (CWE-113).

        Returns:
            The sanitized headers dictionary, or None if no headers were provided.

        Raises:
            ValueError: If a CRLF injection pattern is detected in any header key or value.
        """
        if not headers:
            return headers
        for key, value in headers.items():
            # Check both key and value
            if "\n" in str(key) or "\r" in str(key) or "\n" in str(value) or "\r" in str(value):
                # PEP 578: Emit Enterprise security telemetry before crashing
                sys.audit("mailgun.security.header_injection", key)

                msg = f"CRLF injection detected in header: {key}"
                raise ValueError(msg)
        return headers

    @staticmethod
    def validate_no_control_characters(value: str, context: str = "Input") -> None:
        """Poka-yoke: Prevent Control Character Injection (CWE-20 / CWE-113).

        Raises:
            ValueError: If control characters are detected.
        """
        if _CONTROL_CHAR_RE.search(str(value)):
            sys.audit("mailgun.security.control_characters", context)

            msg = f"Security Alert (CWE-20): Control characters detected in {context}: {value!r}"
            raise ValueError(msg)

    @classmethod
    def sanitize_path_segment(cls, segment: Any) -> str:
        """Poka-yoke: URL-encode path segments and prevent Path Traversal/Injection.

        Returns:
            The URL-encoded path segment string.

        Raises:
            TypeError: If the segment is not a string, int, or float.
            ValueError: If path traversal or invalid characters are detected.
        """
        if segment is None:
            return ""

        if isinstance(segment, (dict, list, set, bool)):
            msg = f"Security Alert: Invalid segment type {type(segment).__name__}."
            raise TypeError(msg)

        raw_str = str(segment)

        # CWE-116: Defeat Double-Encoding bypasses
        decoded = raw_str
        for _ in range(3):
            new_decoded = unquote(decoded)
            if new_decoded == decoded:
                break
            decoded = new_decoded
        else:
            raise ValueError("Security Alert (CWE-116): Excessive URL encoding detected.")

        # CWE-128: Unicode Normalization
        decoded = unicodedata.normalize("NFKC", decoded)

        # 1. CWE-20: Strict path validation
        if _PATH_CONTROL_CHAR_RE.search(decoded):
            if "sys" in sys.modules:
                sys.audit("mailgun.security.control_characters", "path_segment")
            raise ValueError("Security Alert (CWE-20): Forbidden control characters.")

        # 2. CWE-22: Path Traversal
        if ".." in decoded or "/" in decoded or "\\" in decoded:
            if "sys" in sys.modules:
                sys.audit("mailgun.security.path_traversal", decoded)
            raise ValueError("Security Alert (CWE-22): Path traversal attempt.")

        # 3. CWE-94: Template Injection
        if any(marker in decoded for marker in ("{{", "}}", "{%")):
            raise ValueError("Security Alert (CWE-94): Template injection attempt.")

        # 4. CWE-79: XSS
        if _XSS_PATTERN.search(decoded):
            raise ValueError("Security Alert (CWE-79): XSS attempt detected.")

        return quote(decoded, safe="")

    @staticmethod
    def validate_mailgun_url(url: str) -> str:
        """Poka-yoke: Protection against SSRF and API key leakage (CWE-918).

        Returns:
            The validated URL string.

        Raises:
            ValueError: If the URL scheme or host is invalid.
        """
        try:
            parsed = urlparse(url)
            hostname = (parsed.hostname or "").lower()
            scheme = (parsed.scheme or "").lower()
        except ValueError as err:
            raise ValueError("Security Alert: Invalid URL format.") from err

        if not hostname:
            raise ValueError("Security Alert: Missing hostname in URL.")

        if scheme and scheme not in ALLOWED_SCHEMES:
            sys.audit("mailgun.security.ssrf_scheme_violation", scheme)
            msg = f"Security Alert (CWE-319): Forbidden URL scheme '{scheme}'."
            raise ValueError(msg)

        if scheme == "http" and hostname not in {"localhost", "127.0.0.1"}:
            raise ValueError(
                "Security Alert (CWE-319): Plaintext HTTP is forbidden for external URLs."
            )

        is_safe = hostname in ALLOWED_HOSTS or hostname.endswith(ALLOWED_SUFFIXES)

        if not is_safe:
            sys.audit("mailgun.security.ssrf_attempt", url)
            msg = f"Security Alert (CWE-918): Untrusted external hostname '{hostname}'."
            raise ValueError(msg)

        return url

    @staticmethod
    def validate_attachment_path(file_path: str | Path, safe_base_dir: str | Path) -> Path:
        """Poka-yoke: Prevent Path Traversal (CWE-22) when reading attachments.

        Args:
            file_path: The requested file to attach.
            safe_base_dir: The directory that the file MUST reside within.

        Returns:
            A fully resolved, safe Path object.

        Raises:
            ValueError: If the resolved path escapes the safe base directory.
            FileNotFoundError: If the file does not exist.
        """
        target = Path(file_path).resolve()
        base = Path(safe_base_dir).resolve()

        if not target.is_relative_to(base):
            sys.audit("mailgun.security.path_traversal_attempt", str(target))
            msg = (
                f"Security Alert (CWE-22): Path traversal blocked. "
                f"File {target} is outside of safe directory {base}."
            )
            raise ValueError(msg)

        if not target.exists() or not target.is_file():
            msg = f"Attachment not found or is not a file: {target}"
            raise FileNotFoundError(msg)

        return target

    @staticmethod
    def check_file_size(file_path: str | Path, max_size_mb: int = 25) -> None:
        """Guardrail against Out-Of-Memory (OOM) / CWE-400 resource exhaustion.

        Mailgun's API strictly rejects payloads > 25MB. We should fail-fast locally
        instead of wasting memory reading it and wasting bandwidth sending it.

        Raises:
            ValueError: If the file exceeds the maximum allowed size.
        """
        path = Path(file_path)
        size_bytes = Path(path).stat().st_size
        max_bytes = max_size_mb * 1024 * 1024

        if size_bytes > max_bytes:
            msg = (
                f"Security Alert (CWE-400): File exceeds Mailgun's {max_size_mb}MB limit. "
                f"Detected size: {size_bytes / (1024 * 1024):.2f}MB."
            )
            raise ValueError(msg)

    @staticmethod
    def sanitize_log_trace(value: Any) -> str:
        """Centralized CWE-117 Log Forging protection.

        Returns:
            The sanitized string safe for logging.
        """
        # Force cast to string safely to avoid AttributeError on dicts/ints
        safe_str = str(value)
        # _PATH_CONTROL_CHAR_RE is already defined in your security.py
        return _PATH_CONTROL_CHAR_RE.sub("_", safe_str)
