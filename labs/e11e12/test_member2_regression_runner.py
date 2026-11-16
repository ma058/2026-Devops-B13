"""Same-name test modules must be discovered from the selected suite."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class Member2RegressionDiscovery(unittest.TestCase):
    def check_suite(self, selected):
        driver = Path(__file__).resolve().parents[2] / 'course/e11-e12/run_member2_regressions.py'
        with tempfile.TemporaryDirectory(prefix='member2-discovery-') as temporary:
            root = Path(temporary)
            for name in ('e11e12', 'e8e10'):
                directory = root / 'labs' / name
                directory.mkdir(parents=True)
                (directory / 'test_member3.py').write_text(
                    'import unittest\n'
                    'class Example(unittest.TestCase):\n'
                    '    def test_origin(self):\n'
                    '        self.assertTrue(True)\n', encoding='utf-8')
            code = '''
import importlib.util, json, pathlib, sys, unittest
spec = importlib.util.spec_from_file_location('member2_driver', sys.argv[1])
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
root = pathlib.Path(sys.argv[2])
# Reproduce the host PYTHONPATH order, including an already-present start_dir.
sys.path[:0] = [str(root/'labs/e11e12'), str(root/'labs/e8e10')]
suite = driver.discover_suite(root, sys.argv[3])
result = unittest.TextTestRunner().run(suite)
print(json.dumps({'origin':str(pathlib.Path(sys.modules['test_member3'].__file__).resolve()),
                  'tests_run':result.testsRun,'passed':result.wasSuccessful()}))
'''
            result = subprocess.run([sys.executable, '-c', code, str(driver), str(root), selected],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            observed = json.loads(result.stdout)
            self.assertEqual(Path(observed['origin']), (root/'labs'/selected/'test_member3.py').resolve())
            self.assertEqual(observed['tests_run'], 1)
            self.assertTrue(observed['passed'])

    def test_e8e10_uses_its_own_member3_module(self):
        self.check_suite('e8e10')

    def test_e11e12_uses_its_own_member3_module(self):
        self.check_suite('e11e12')


if __name__ == '__main__':
    unittest.main()
