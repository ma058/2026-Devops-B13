"""Retain regression summaries; skips are not accepted as a passing gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--suite',choices=['e11e12','e8e10'],required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    root=Path(__file__).resolve().parents[2]
    output=args.out.resolve()
    if os.name!='posix' or (root/'work').resolve() not in output.parents or output.exists():
        p.error('Use Linux and a new OUT below work/')
    output.mkdir(parents=True)
    os.environ['M2_E11E12_TEST_OUT']=str(output/'member2-cases')
    sys.path[:0]=[str(root/'labs/e11e12'),str(root/'labs/e8e10')]
    suite=unittest.defaultTestLoader.discover(str(root/'labs'/args.suite),pattern='test_*.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    summary={'status':'PASS' if result.wasSuccessful() and result.testsRun and not result.skipped else 'FAIL',
        'suite':args.suite,'tests_run':result.testsRun,'skipped':result.skipped,
        'failures':[(str(test),trace) for test,trace in result.failures],
        'errors':[(str(test),trace) for test,trace in result.errors],
        'test_sha256':{path.name:hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in sorted((root/'labs'/args.suite).glob('test_*.py'))}}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)
    return 0 if summary['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
