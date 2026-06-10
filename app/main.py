from __future__ import annotations

import argparse

from app.bootstrap import bootstrap_app
from app.ui.web_server import DEFAULT_HOST, DEFAULT_PORT, run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="SteamSearch application entry point.")
    subparsers = parser.add_subparsers(dest="command")

    web_parser = subparsers.add_parser("web", help="Run the lightweight browser UI.")
    web_parser.add_argument("--host", default=DEFAULT_HOST)
    web_parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    web_parser.add_argument("--no-demo-data", action="store_true")

    subparsers.add_parser("check", help="Run bootstrap checks without starting the web UI.")

    args = parser.parse_args()
    if args.command == "check":
        run_check()
        return

    run_server(
        host=getattr(args, "host", DEFAULT_HOST),
        port=getattr(args, "port", DEFAULT_PORT),
        no_demo_data=getattr(args, "no_demo_data", False),
    )


def run_check() -> None:
    context = bootstrap_app()
    print("SteamSearch bootstrap complete")
    print(f"config: {context.config_path}")
    print(f"database: {context.settings.app.database_path}")
    print(f"log: {context.settings.app.log_path}")
    context.database.close()


if __name__ == "__main__":
    main()
