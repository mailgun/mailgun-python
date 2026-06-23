#!/usr/bin/env python3

import sys
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.builders import MailgunMessageBuilder, MailgunTemplateBuilder


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    try:
        target_builder = fdp.ConsumeIntInRange(0, 1)

        if target_builder == 0:
            from_email = fdp.ConsumeUnicodeNoSurrogates(30)
            builder = MailgunMessageBuilder(from_email)

            num_operations = fdp.ConsumeIntInRange(1, 20)
            for _ in range(num_operations):
                op_code = fdp.ConsumeIntInRange(0, 7)

                if op_code == 0:
                    builder.add_custom_header(
                        fdp.ConsumeUnicodeNoSurrogates(20),
                        fdp.ConsumeUnicodeNoSurrogates(100),
                    )
                elif op_code == 1:
                    val_type = fdp.ConsumeIntInRange(0, 3)
                    val: Any = None
                    if val_type == 0:
                        val = fdp.ConsumeUnicodeNoSurrogates(50)
                    elif val_type == 1:
                        val = fdp.ConsumeInt(8)
                    elif val_type == 2:
                        val = fdp.ConsumeBool()
                    else:
                        val = {
                            fdp.ConsumeUnicodeNoSurrogates(
                                10
                            ): fdp.ConsumeUnicodeNoSurrogates(20)
                        }
                    builder.add_custom_variable(fdp.ConsumeUnicodeNoSurrogates(20), val)
                elif op_code == 2:
                    opt_val = fdp.PickValueInList(
                        [True, False, fdp.ConsumeUnicodeNoSurrogates(10)]
                    )
                    builder.add_option(fdp.ConsumeUnicodeNoSurrogates(20), value=opt_val)
                elif op_code == 3:
                    rec_type = fdp.PickValueInList(
                        ["bcc", "cc", "to", fdp.ConsumeUnicodeNoSurrogates(5)]
                    )
                    try:
                        builder.add_recipient(
                            fdp.ConsumeUnicodeNoSurrogates(30), rec_type
                        )
                    except ValueError:
                        # Fuzz input can generate invalid recipient types/values.
                        # Ignore expected ValueError here and continue exploring.
                        pass
                elif op_code == 4:
                    builder.set_html(fdp.ConsumeUnicodeNoSurrogates(500))
                elif op_code == 5:
                    builder.set_subject(fdp.ConsumeUnicodeNoSurrogates(100))
                elif op_code == 6:
                    builder.set_template(fdp.ConsumeUnicodeNoSurrogates(20))
                elif op_code == 7:
                    builder.set_text(fdp.ConsumeUnicodeNoSurrogates(500))

            _ = builder.build()

        else:
            if fdp.ConsumeBool():
                template_name = fdp.ConsumeUnicodeNoSurrogates(30)
                try:
                    t_builder = MailgunTemplateBuilder(template_name)
                except ValueError:
                    return
            else:
                t_builder = MailgunTemplateBuilder()

            num_operations = fdp.ConsumeIntInRange(1, 10)
            for _ in range(num_operations):
                op_code = fdp.ConsumeIntInRange(0, 7)

                if op_code == 0:
                    t_builder.set_active(active=fdp.ConsumeBool())
                elif op_code == 1:
                    acc = fdp.ConsumeUnicodeNoSurrogates(10)
                    name = fdp.ConsumeUnicodeNoSurrogates(10)
                    t_builder.set_copy_requests([{"account_id": acc, "name": name}])
                elif op_code == 2:
                    t_builder.set_description(fdp.ConsumeUnicodeNoSurrogates(100))
                elif op_code == 3:
                    t_builder.set_engine(
                        fdp.PickValueInList(
                            ["handlebars", "jinja2", fdp.ConsumeUnicodeNoSurrogates(10)]
                        )
                    )
                elif op_code == 4:
                    key = fdp.ConsumeUnicodeNoSurrogates(10)
                    t_val = fdp.ConsumeUnicodeNoSurrogates(20)
                    t_builder.set_headers({key: t_val})
                elif op_code == 5:
                    t_builder.set_tag(fdp.ConsumeUnicodeNoSurrogates(20))
                elif op_code == 6:
                    try:
                        t_builder.set_template_content(
                            fdp.ConsumeUnicodeNoSurrogates(500)
                        )
                    except ValueError:
                        pass
                elif op_code == 7:
                    t_builder.set_version_comment(fdp.ConsumeUnicodeNoSurrogates(100))

            try:
                t_builder.build()
            except ValueError:
                pass

    except ValueError as e:
        error_msg = str(e)
        allowed_errors = [
            "Cannot build an empty template payload",
            "Cannot build template payload without template content",
            "Exceeds the limit",
            "Invalid recipient type",
            "Security Alert (CWE-400)",
            "Template content cannot be empty",
            "Template name cannot be empty",
        ]

        if not any(msg in error_msg for msg in allowed_errors):
            raise


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
