import argparse
import tempfile
import traceback
from typing import Callable

from pwt.winenv_cli.ui.base import UIProtocol, UIRegistry


def create_ui_from_args(argv: list[str] | None = None) -> tuple[UIProtocol, list[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    for name, func in UIRegistry.registry.items():
        parser.add_argument(
            f"--{name}",
            dest="ui",
            action="store_const",
            const=func,
        )
    parser.set_defaults(ui=UIRegistry.get_default())
    args, argv = parser.parse_known_args(argv)
    return args.ui(), argv


def run_app(main_func: Callable[[UIProtocol, list[str]], int]) -> int:
    """CLI 程序的统一入口包装器"""
    ui, argv = create_ui_from_args()

    try:
        return main_func(ui, argv)
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        ui.error(f"Exception occurred: {exc.__class__.__name__} - {exc!s}")
        return 1
    except KeyboardInterrupt:
        ui.render("Received SIGINT signal, Exiting...")
        return 130
    except EOFError:
        ui.render("Received unexpected EOF, Exiting...")
        return 130
    except Exception as exc:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix="traceback-", suffix=".log", delete=False
        ) as file:
            traceback.print_exception(exc, file=file)
            ui.error(
                f"Error occurred: {exc.__class__.__name__} - {exc!s}\n"
                f"Unexpected error. Traceback log at: {file.name}"
            )
        return 1
