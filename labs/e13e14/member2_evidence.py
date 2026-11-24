"""Select and scan the runtime files that may enter a shared evidence export."""
import argparse
from pathlib import Path

import scan_runtime_logs


PRIVATE_FILES = frozenset(('token.secret', 'roles.secret.env'))


def evidence_files(run):
    run = Path(run)
    private = {run / name for name in PRIVATE_FILES}
    return [path for path in sorted(run.rglob('*'))
            if path.is_file() and not path.is_symlink()
            and '.git' not in path.parts and path not in private]


def scan_evidence(run):
    # The report is opened by shell redirection before this function executes;
    # it must not count as readable evidence or scan itself on later exports.
    run = Path(run)
    files = [p for p in evidence_files(run) if p != run / 'diagnostics-scan.log']
    if not files:
        print('SCAN_ERROR no exportable runtime evidence')
        return 2
    return scan_runtime_logs.main([str(path) for path in files])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    raise SystemExit(scan_evidence(parser.parse_args().run))
