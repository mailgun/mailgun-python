import importlib
import sys
from unittest.mock import patch


class TestTypesCompatibility:
    def test_types_python_310_fallback(self) -> None:
        """
        Ensures that the SDK correctly imports `TypedDict` and `NotRequired`
        from `typing_extensions` on Python versions older than 3.11.
        """
        import mailgun.types

        with patch.object(sys, "version_info", (3, 10)):
            # Force Python to re-evaluate the module level if-statement
            importlib.reload(mailgun.types)
            assert hasattr(mailgun.types, "TypedDict")
            assert hasattr(mailgun.types, "NotRequired")

        # Restore normal state for downstream tests
        importlib.reload(mailgun.types)
