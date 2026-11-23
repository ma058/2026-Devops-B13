"""Versioned E14 entrypoint; legacy course CI remains explicitly separate."""
import os
import runpy
from pathlib import Path

if __name__ == "__main__":
    protocol = os.environ.get("E14_PROTOCOL", "teaching-template")
    if protocol == "member2-e14-1":
        from member2_service import main
        main()
    elif protocol == "teaching-template":
        runpy.run_path(str(Path(__file__).with_name("teaching_service.py")), run_name="__main__")
    else:
        raise SystemExit("UNSUPPORTED_PROTOCOL")
