from __future__ import annotations


def main() -> None:
    try:
        from ui import OpsConsoleApp
    except Exception as exc:
        print(exc)
        raise SystemExit(1)

    app = OpsConsoleApp()
    app.run(None)


if __name__ == "__main__":
    main()
