import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from atelier.core import Paths
ROOT=Path(__file__).resolve().parents[2]

class QuickPicker(unittest.TestCase):
    def load(self):
        spec=importlib.util.spec_from_file_location('quick_bridge',ROOT/'packaging/engine_bridge.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module
    def test_native_picker_result_is_forwarded(self):
        with tempfile.TemporaryDirectory() as temp:
            paths=Paths(home=Path(temp));paths.helper.mkdir(parents=True)
            (paths.helper/'picker.py').write_text('import json\ndef pick(selected):\n print(json.dumps({"path":selected,"project":"/workshop/123"}))\n')
            module=self.load();output=io.StringIO()
            with patch.object(module,'Paths',return_value=paths),patch.object(sys,'argv',['engine_bridge.py','pick','/preview.jpg']),contextlib.redirect_stdout(output):
                module.main()
            self.assertEqual(json.loads(output.getvalue()),{'path':'/preview.jpg','project':'/workshop/123'})
    def test_cancel_does_not_apply_anything(self):
        with tempfile.TemporaryDirectory() as temp:
            paths=Paths(home=Path(temp));paths.helper.mkdir(parents=True)
            (paths.helper/'picker.py').write_text('def pick(selected):\n pass\n')
            module=self.load();output=io.StringIO()
            with patch.object(module,'Paths',return_value=paths),patch.object(sys,'argv',['engine_bridge.py','pick']),patch.object(module.os,'execv') as render,contextlib.redirect_stdout(output):
                module.main()
            self.assertEqual(output.getvalue(),'');render.assert_not_called()
    def test_desktop_uses_native_picker_not_full_application(self):
        candidate=(ROOT/'packaging/Background.qml').read_text()
        selector=candidate.split('  function openSelector(screenName) {',1)[1].split('\n  }',1)[0]
        self.assertIn('"pick", monitorBackground(screenName) || currentBackground',selector)
        self.assertIn('bgSwitchProc.running = true',selector)
        self.assertNotIn('run-atelier',selector)
        self.assertNotIn('Qt.RightButton',candidate)
        self.assertIn('function atelierApply',candidate)
