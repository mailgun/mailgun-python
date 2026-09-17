#!/usr/bin/env python3
"""Fuzzer for Message and Template Builders targeting RFC2822, MIME, and Template ASTs."""

import logging
import sys
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.builders import MailgunMessageBuilder, MailgunTemplateBuilder

logging.disable(logging.CRITICAL)

_ALLOWED_ERRORS = [
    "Cannot build an empty template payload",
    "Cannot build template payload without template content",
    "Exceeds the limit",
    "Invalid recipient type",
    "Security Alert (CWE-20)",
    "Security Alert (CWE-113)",
    "Security Alert (CWE-400)",
    "Template content cannot be empty",
    "Template name cannot be empty",
    "Invalid email address",
    "Header injection detected",
]


def TestOneInput(data: bytes) -> None:
    if len(data) < 15:
        return

    fdp = atheris.FuzzedDataProvider(data)

    try:
        if fdp.ConsumeBool():
            # Target 1: MailgunMessageBuilder
            from_email = fdp.ConsumeUnicodeNoSurrogates(30)
            builder = MailgunMessageBuilder(from_email)

            for _ in range(fdp.ConsumeIntInRange(1, 15)):
                op_code = fdp.ConsumeIntInRange(0, 8)

                if op_code == 0:
                    builder.add_custom_header(
                        fdp.ConsumeUnicodeNoSurrogates(20),
                        fdp.ConsumeUnicodeNoSurrogates(100),
                    )
                elif op_code == 1:
                    val: Any = (
                        fdp.ConsumeUnicodeNoSurrogates(40)
                        if fdp.ConsumeBool()
                        else {"k": fdp.ConsumeUnicodeNoSurrogates(20)}
                    )
                    builder.add_custom_variable(fdp.ConsumeUnicodeNoSurrogates(20), val)
                elif op_code == 2:
                    builder.add_option(
                        fdp.ConsumeUnicodeNoSurrogates(20),
                        value=fdp.PickValueInList([True, False, fdp.ConsumeUnicodeNoSurrogates(10)]),
                    )
                elif op_code == 3:
                    builder.add_recipient(
                        fdp.ConsumeUnicodeNoSurrogates(30),
                        recipient_type=fdp.PickValueInList(["to", "cc", "bcc", "invalid"]),
                    )
                elif op_code == 4:
                    builder.set_html(fdp.ConsumeUnicodeNoSurrogates(200))
                elif op_code == 5:
                    builder.set_subject(fdp.ConsumeUnicodeNoSurrogates(100))
                elif op_code == 6:
                    builder.set_template(fdp.ConsumeUnicodeNoSurrogates(20))
                elif op_code == 7:
                    builder.set_text(fdp.ConsumeUnicodeNoSurrogates(200))
                elif op_code == 8:
                    builder.add_option(
                        "deliverytime",
                        value=fdp.ConsumeUnicodeNoSurrogates(30),
                    )

            _ = builder.build()

        else:
            # Target 2: MailgunTemplateBuilder
            template_name = (
                fdp.ConsumeUnicodeNoSurrogates(30) if fdp.ConsumeBool() else None
            )
            t_builder = (
                MailgunTemplateBuilder(template_name)
                if template_name
                else MailgunTemplateBuilder()
            )

            for _ in range(fdp.ConsumeIntInRange(1, 8)):
                op = fdp.ConsumeIntInRange(0, 4)
                if op == 0:
                    t_builder.set_active(active=fdp.ConsumeBool())
                elif op == 1:
                    t_builder.set_description(fdp.ConsumeUnicodeNoSurrogates(50))
                elif op == 2:
                    t_builder.set_engine(
                        fdp.PickValueInList(["handlebars", "jinja2", "{{7*7}}", "none"])
                    )
                elif op == 3:
                    t_builder.set_template_content(fdp.ConsumeUnicodeNoSurrogates(200))
                elif op == 4:
                    t_builder.set_tag(fdp.ConsumeUnicodeNoSurrogates(20))

            _ = t_builder.build()


    except (ValueError, AttributeError) as e:
        error_msg = str(e)
        if isinstance(e, ValueError) and not any(msg in error_msg for msg in _ALLOWED_ERRORS):
            raise RuntimeError(f"CRASH: Unexpected ValueError in builders: {e}") from e
    except TypeError:
        # Fuzzed inputs may intentionally violate builder method contracts; ignore and continue fuzzing.
        return
    except Exception as e:
        raise RuntimeError(f"UNHANDLED CRASH in Builders execution: {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
