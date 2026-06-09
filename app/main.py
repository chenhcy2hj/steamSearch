from __future__ import annotations

from app.bootstrap import bootstrap_app


def main() -> None:
    context = bootstrap_app()
    print("SteamSearch bootstrap complete")
    print(f"config: {context.config_path}")
    print(f"database: {context.settings.app.database_path}")
    print(f"log: {context.settings.app.log_path}")


if __name__ == "__main__":
    main()

