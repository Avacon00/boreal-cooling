"""Private line-delimited worker protocol. Parent enforces operation deadlines."""
import json
import logging
import sys
from .hardware import DemoHardware, LiquidHardware

ALLOWED = {"discover", "attach", "status", "curves", "fallback", "screen", "color", "detach", "close", "display_info"}


def main(demo=False):
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    backend = None
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if request["op"] not in ALLOWED:
                raise ValueError("Unknown worker operation")
            if backend is None:
                backend = DemoHardware() if demo else LiquidHardware()
            result = getattr(backend, request["op"])(*request.get("args", []))
            response = {"ok": True, "result": result}
        except Exception as exc:
            response = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(response, allow_nan=False), flush=True)
    if backend:
        backend.close()


if __name__ == "__main__":
    main("--demo" in sys.argv)
