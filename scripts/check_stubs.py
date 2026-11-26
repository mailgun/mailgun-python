# ruff: file-ignore[implicit-namespace-package]
"""Deterministic PEP 484 (.pyi) stub generator and drift checker for mailgun.

Uses pure Python AST parsing (zero subprocess calls) so `--write` and `--check`
produce reproducible stubs across Python environments and CI runners.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import sys
from operator import itemgetter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
_ROUTE_DICT_NAMES = frozenset({"_EXACT_ROUTES", "_PREFIX_ROUTES", "_ROUTE_ALIASES"})


def _default_package_dir() -> Path:
    repo_pkg = REPO_ROOT / "mailgun"
    if repo_pkg.is_dir():
        return repo_pkg
    spec = importlib.util.find_spec("mailgun")
    if spec is not None and spec.origin is not None:
        return Path(spec.origin).resolve().parent
    return repo_pkg


def _format_arg(arg: ast.arg, default: ast.expr | None) -> str:
    text = arg.arg
    if arg.annotation is not None:
        text = f"{text}: {ast.unparse(arg.annotation)}"
    if default is not None:
        text = f"{text} = ..."
    return text


def _is_async_generator(node: ast.AsyncFunctionDef) -> bool:
    stack: list[ast.AST] = list(node.body)
    while stack:
        stmt = stack.pop()
        if isinstance(stmt, (ast.Yield, ast.YieldFrom)):
            return True
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        stack.extend(ast.iter_child_nodes(stmt))
    return False


def _format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = node.args
    parts: list[str] = []

    positional = list(args.posonlyargs) + list(args.args)
    pos_defaults: list[ast.expr | None] = [None] * (len(positional) - len(args.defaults)) + list(
        args.defaults
    )

    for idx, (arg, default) in enumerate(zip(positional, pos_defaults, strict=True)):
        parts.append(_format_arg(arg, default))
        if args.posonlyargs and idx == len(args.posonlyargs) - 1:
            parts.append("/")

    if args.vararg is not None:
        parts.append(f"*{_format_arg(args.vararg, None)}")
    elif args.kwonlyargs:
        parts.append("*")

    for kwarg, kw_default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
        parts.append(_format_arg(kwarg, kw_default))

    if args.kwarg is not None:
        parts.append(f"**{_format_arg(args.kwarg, None)}")

    ret = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    prefix = (
        "async def"
        if isinstance(node, ast.AsyncFunctionDef) and not _is_async_generator(node)
        else "def"
    )
    return f"{prefix} {node.name}({', '.join(parts)}){ret}: ..."


def _extract_route_names(routes_source: str) -> list[str]:
    tree = ast.parse(routes_source)
    found_dicts: set[str] = set()
    names: set[str] = set()

    for node in tree.body:
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value

        matched = [t.id for t in targets if isinstance(t, ast.Name) and t.id in _ROUTE_DICT_NAMES]
        if matched and isinstance(value, ast.Dict):
            found_dicts.update(matched)
            for key in value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    names.add(key.value)

    missing = _ROUTE_DICT_NAMES - found_dicts
    if missing:
        msg = f"Unable to locate route dictionaries in mailgun/routes.py: {sorted(missing)}"
        raise RuntimeError(msg)

    return sorted(names)


def _find_class(tree: ast.Module, class_name: str) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    msg = f"Class {class_name!r} not found in AST"
    raise RuntimeError(msg)


def _is_overload_decorator(dec: ast.expr) -> bool:
    return (isinstance(dec, ast.Name) and dec.id == "overload") or (
        isinstance(dec, ast.Attribute) and dec.attr == "overload"
    )


def _extract_all_exports(tree: ast.Module) -> list[str]:
    for node in tree.body:
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        if any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets) and isinstance(
            value, (ast.List, ast.Tuple)
        ):
            return [
                elt.value
                for elt in value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]
    msg = "Unable to locate __all__ exports in module AST"
    raise RuntimeError(msg)


def _format_all_block(exports: list[str]) -> list[str]:
    small_export_limit = 3
    if len(exports) <= small_export_limit:
        rendered = ", ".join(f'"{name}"' for name in exports)
        return [f"__all__ = [{rendered}]"]
    lines = ["__all__ = ["]
    lines.extend(f'    "{name}",' for name in exports)
    lines.append("]")
    return lines


def _extract_class_annassigns(cls_node: ast.ClassDef) -> list[str]:
    entries: list[tuple[int, str, str]] = []
    for item in cls_node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            ann = ast.unparse(item.annotation)
            name = item.target.id
            rank = 0 if "ClassVar[" in ann else 1
            entries.append((rank, name, f"    {name}: {ann}"))
    entries.sort(key=itemgetter(0, 1))
    return [line for _, _, line in entries]


def _extract_reserved_attrs(*classes: ast.ClassDef) -> set[str]:
    reserved: set[str] = {"__getattr__"}
    for cls_node in classes:
        for item in cls_node.body:
            if isinstance(
                item, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and not item.name.startswith("_"):
                reserved.add(item.name)
            elif (
                isinstance(item, ast.AnnAssign)
                and isinstance(item.target, ast.Name)
                and not item.target.id.startswith("_")
            ):
                reserved.add(item.target.id)
    return reserved


def _format_class_methods(cls_node: ast.ClassDef) -> list[str]:
    overloaded = {
        item.name
        for item in cls_node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(_is_overload_decorator(dec) for dec in item.decorator_list)
    }
    lines: list[str] = []
    for item in cls_node.body:
        if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if item.name in {"__repr__", "__str__"}:
            continue
        has_overload = any(_is_overload_decorator(dec) for dec in item.decorator_list)
        if item.name in overloaded and not has_overload:
            continue
        lines.extend(f"    @{ast.unparse(dec)}" for dec in item.decorator_list)
        lines.append(f"    {_format_signature(item)}")
    return lines


def _format_top_functions(tree: ast.Module, func_names: tuple[str, ...]) -> list[str]:
    overloaded = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in func_names
        and any(_is_overload_decorator(dec) for dec in node.decorator_list)
    }
    lines: list[str] = []
    for func_name in func_names:
        matched = [
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name
        ]
        if not matched:
            msg = f"Function {func_name!r} not found in AST"
            raise RuntimeError(msg)
        for node in matched:
            has_overload = any(_is_overload_decorator(dec) for dec in node.decorator_list)
            if func_name in overloaded and not has_overload:
                continue
            lines.extend(f"@{ast.unparse(dec)}" for dec in node.decorator_list)
            lines.append(_format_signature(node))
    return lines


def _tree_has_overloads(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
            _is_overload_decorator(dec) for dec in node.decorator_list
        ):
            return True
    return False


def render_endpoints_stub(package_dir: Path) -> str:
    """Render deterministic stub content for mailgun/endpoints.pyi.

    Returns:
        str: Formatted PEP 484 stub source for `mailgun/endpoints.py`.
    """
    tree = ast.parse((package_dir / "endpoints.py").read_text(encoding="utf-8"))
    base_cls = _find_class(tree, "BaseEndpoint")
    ep_cls = _find_class(tree, "Endpoint")
    async_ep_cls = _find_class(tree, "AsyncEndpoint")
    typing_names = "Any, overload" if _tree_has_overloads(tree) else "Any"

    lines = [
        "# Generated by scripts/check_stubs.py --write. Do not edit manually.",
        "# ruff: file-ignore[async-function-with-timeout]",
        "import logging",
        "from collections.abc import Iterable, Mapping",
        f"from typing import {typing_names}",
        "",
        "import httpx2 as _httpx2_mod",
        "import requests",
        "",
        "from mailgun.config import RetryPolicy",
        "from mailgun.types import APIResponseType, AsyncAPIResponseType, TimeoutType",
        "",
        "httpx2: Any",
        "logger: logging.Logger",
        "",
        *_format_top_functions(tree, ("build_path_from_keys",)),
        "",
        "class BaseEndpoint:",
        "    headers: dict[str, str]",
        "    dry_run: bool",
        "    retry_policy: RetryPolicy | None",
        *_extract_class_annassigns(base_cls),
        *_format_class_methods(base_cls),
        "",
        "class Endpoint(BaseEndpoint):",
        *_extract_class_annassigns(ep_cls),
        *_format_class_methods(ep_cls),
        "",
        "class AsyncEndpoint(BaseEndpoint):",
        *_extract_class_annassigns(async_ep_cls),
        *_format_class_methods(async_ep_cls),
        "",
    ]
    return "\n".join(lines)


def _format_route_properties(
    routes: list[str],
    reserved_attrs: set[str],
    endpoint_cls_name: str,
) -> list[str]:
    lines: list[str] = []
    for route in routes:
        if route not in reserved_attrs and route.isidentifier():
            lines.extend(("    @property", f"    def {route}(self) -> {endpoint_cls_name}: ..."))
    return lines


def render_client_stub(package_dir: Path) -> str:
    """Render deterministic stub content for mailgun/client.pyi.

    Returns:
        str: Formatted PEP 484 stub source for `mailgun/client.py`.
    """
    tree = ast.parse((package_dir / "client.py").read_text(encoding="utf-8"))
    routes = _extract_route_names((package_dir / "routes.py").read_text(encoding="utf-8"))

    base_client_cls = _find_class(tree, "BaseClient")
    client_cls = _find_class(tree, "Client")
    async_client_cls = _find_class(tree, "AsyncClient")
    exports = _extract_all_exports(tree)
    reserved_attrs = _extract_reserved_attrs(base_client_cls, client_cls, async_client_cls)
    reserved_attrs.update({"auth", "config", "timeout", "endpoint_cls"})
    typing_names = "Any, Self, overload" if _tree_has_overloads(tree) else "Any, Self"

    lines = [
        "# Generated by scripts/check_stubs.py --write. Do not edit manually.",
        "# ruff: file-ignore[unsorted-imports]",
        "import types",
        f"from typing import {typing_names}",
        "",
        "import httpx2 as _httpx2_mod",
        "import requests",
        "",
        "from mailgun.config import Config as Config",
        "from mailgun.endpoints import AsyncEndpoint as AsyncEndpoint, BaseEndpoint as BaseEndpoint, Endpoint as Endpoint",
        "from mailgun.filters import RedactingFilter as RedactingFilter",
        "from mailgun.security import (",
        "    SecretAuth as SecretAuth,",
        "    SecureHTTPAdapter as SecureHTTPAdapter,",
        "    SecurityGuard as SecurityGuard,",
        ")",
        "",
        *_format_all_block(exports),
        "",
        "httpx2: Any",
        "",
        "class BaseClient:",
        "    auth: tuple[str, str] | None",
        "    config: Config",
        "    timeout: Any",
        *_extract_class_annassigns(base_client_cls),
        *_format_class_methods(base_client_cls),
        "",
        "class Client(BaseClient):",
        *_extract_class_annassigns(client_cls),
        *_format_class_methods(client_cls),
        *_format_route_properties(routes, reserved_attrs, "Endpoint"),
        "",
        "class AsyncClient(BaseClient):",
        "    endpoint_cls: type[AsyncEndpoint]",
        *_extract_class_annassigns(async_client_cls),
        *_format_class_methods(async_client_cls),
        *_format_route_properties(routes, reserved_attrs, "AsyncEndpoint"),
        "",
    ]
    return "\n".join(lines)


def expected_stubs(package_dir: Path) -> dict[Path, str]:
    """Compute expected stub file paths and deterministic contents for a package directory.

    Returns:
        dict[Path, str]: Mapping from stub `.pyi` path to expected deterministic text.
    """
    resolved_dir = package_dir.resolve()
    return {
        resolved_dir / "endpoints.pyi": render_endpoints_stub(resolved_dir),
        resolved_dir / "client.pyi": render_client_stub(resolved_dir),
    }


def check_or_write_stubs(package_dir: Path, *, write: bool) -> list[Path]:
    """Check stub files for drift or overwrite them when `write=True`.

    Returns:
        list[Path]: Paths that differed from deterministic output (or were updated).
    """
    drifted: list[Path] = []
    for stub_path, rendered in expected_stubs(package_dir).items():
        current = stub_path.read_text(encoding="utf-8") if stub_path.exists() else None
        if current != rendered:
            drifted.append(stub_path)
            if write:
                stub_path.write_text(rendered, encoding="utf-8")
    return drifted


def main(argv: list[str] | None = None) -> int:
    """CLI entry point supporting `--write` and `--check`.

    Returns:
        int: Process exit code (`0` when synchronized, `1` when drift is detected).
    """
    parser = argparse.ArgumentParser(
        description="Generate or verify tracked .pyi stubs for mailgun."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Write deterministic .pyi stub files.")
    mode.add_argument(
        "--check", action="store_true", help="Fail if any .pyi stub drifted from source AST."
    )
    parser.add_argument(
        "--package-dir",
        type=Path,
        default=_default_package_dir(),
        help="Path to the mailgun package directory.",
    )
    args = parser.parse_args(argv)

    package_dir = args.package_dir.resolve()
    drifted = check_or_write_stubs(package_dir, write=bool(args.write))

    if args.check:
        if drifted:
            for path in drifted:
                sys.stdout.write(f"Stub drift detected: {path}\n")
            return 1
        sys.stdout.write(f"Stubs up to date ({len(expected_stubs(package_dir))} files verified).\n")
        return 0

    sys.stdout.write(f"Stubs synchronized ({len(drifted)} updated).\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
