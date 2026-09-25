"""Agent-agnostic SDLC harness."""

__version__ = "0.7.6"

# Runs before any other module is compiled, so it must stay parseable by old interpreters: plain syntax, % formatting.
# Without it, Python < 3.11 dies on a `match` statement with a bare SyntaxError, often from inside a git hook.
import sys as _sys

if _sys.version_info[:2] < (3, 11):
    _sys.stderr.write(
        "sdlc-harness %s requires Python 3.11 or newer; this is Python %d.%d.%d (%s).\n"
        "Run it with a newer interpreter, for example: python3.11 .harness/sdlc.pyz <command>\n"
        "If this came from a git hook: the hooks run the first `python3` on PATH, so put a Python 3.11 or newer "
        "first on PATH.\n" % ((__version__,) + tuple(_sys.version_info[:3]) + (_sys.executable,))
    )
    raise SystemExit(2)
