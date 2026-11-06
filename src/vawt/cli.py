"""One entry point, `uv run vawt <command>`. Modules load lazily; no argument lists the commands."""

import importlib
import sys

COMMANDS = {
    "sizing": ("vawt.system.sizing", "power, voltage and structure figures"),
    "docs": (
        "vawt.io.docs",
        "regenerate docs/sizing.md, docs/assumptions.md and CLAUDE's guard rails",
    ),
    "import-turbine": ("vawt.io.import_turbine", "extract the rotor meshes from the 3MF to build/"),
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("commands:", *(f"  {k}  {v[1]}" for k, v in COMMANDS.items()), sep="\n")
        sys.exit(0 if len(sys.argv) < 2 else 2)
    module, _ = COMMANDS[sys.argv[1]]
    sys.argv = [f"vawt {sys.argv[1]}", *sys.argv[2:]]
    importlib.import_module(module).main()


if __name__ == "__main__":
    main()
