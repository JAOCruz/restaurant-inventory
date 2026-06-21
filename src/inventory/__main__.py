"""Entry point for `python -m inventory`.

When you run `python -m inventory`, Python executes this file.  Its only job
is to import and call the main() function from the cli module.  Keeping this
file tiny makes it easy to understand how the command-line entry point works.
"""

from .cli import main

if __name__ == "__main__":
    # raise SystemExit(...) ensures the process exits with the integer returned
    # by main(). 0 means success; 1 or 2 means a specific kind of failure.
    raise SystemExit(main())
