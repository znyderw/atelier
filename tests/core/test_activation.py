import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from activate import activate
from atelier.core import Paths, atomic_json, digest, AtelierError

class Activation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        base=Path(self.temp.name);self.root=base/'app';self.p=Paths(base/'home',base/'stock',base/'data')
        self.p.plugin.parent.mkdir(parents=True);self.p.plugin.write_text('previous plugin')
        default=self.p.user/'default/colors.toml';default.parent.mkdir(parents=True);default.write_text('background="#161e2a"\n')
        atomic_json(self.root/'packaging/migration-plan.json',{'before':digest(self.p.plugin)})
        self.active=False;self.calls=[];self.confirm=True
    def runner(self,args,**kwargs):
        self.calls.append(args)
        if args[0]=='hyprctl': return '[{"name":"DP-1"}]'
        if args[-1]=='atelierCapabilities': return '{"version":1,"apply":true}' if self.active else '{}'
        if any(str(s).endswith('install.py') for s in args):
            self.active=self.confirm;return 'Migração instalada. Backup: /tmp/validated-backup\n'
        return ''
    def test_already_active_does_not_reinstall(self):
        self.active=True
        result=activate(self.root,self.p,self.runner,lambda _:None)
        self.assertTrue(result['alreadyActive'])
        self.assertFalse(any(str(s).endswith('install.py') for call in self.calls for s in call))
    def test_activate_confirms_bridge_and_records_backup(self):
        result=activate(self.root,self.p,self.runner,lambda _:None)
        self.assertFalse(result['alreadyActive'])
        self.assertEqual(result['backup'],'/tmp/validated-backup')
        self.assertTrue((self.p.data/'activation.json').is_file())
        self.assertEqual(self.p.plugin.read_text(),'previous plugin') # fake installer never mutates a real desktop
    def test_missing_confirmation_attempts_guarded_rollback(self):
        self.confirm=False
        with self.assertRaisesRegex(AtelierError,'não confirmou'): activate(self.root,self.p,self.runner,lambda _:None)
        self.assertTrue(any(str(s).endswith('rollback.py') for call in self.calls for s in call))
    def test_plugin_change_fails_before_install(self):
        self.p.plugin.write_text('user change')
        with self.assertRaisesRegex(AtelierError,'alterado'): activate(self.root,self.p,self.runner,lambda _:None)
        self.assertFalse(any(str(s).endswith('install.py') for call in self.calls for s in call))

    def test_error_dialog_escapes_traceback_markup(self):
        import importlib,io
        from unittest.mock import patch
        from contextlib import redirect_stderr
        module=importlib.import_module('activate')
        error='Traceback in <module> & "details"'
        with patch.object(module,'Paths',return_value=self.p),patch.object(module,'activate',side_effect=AtelierError(error)),patch.object(module.subprocess,'run') as dialog,redirect_stderr(io.StringIO()):
            self.assertEqual(module.main(),1)
        text=next(arg for arg in dialog.call_args.args[0] if arg.startswith('--text='))
        self.assertIn('&lt;module&gt;',text)
        self.assertIn('&amp;',text)
        self.assertNotIn('<module>',text)
        self.assertIn(error,(self.p.data/'activation.log').read_text())

    def test_stale_shell_restarted_once_then_bridge_confirms(self):
        self.confirm=False
        def runner(args,**kw):
            value=self.runner(args,**kw)
            if args==['omarchy','restart','shell']: self.active=True
            return value
        result=activate(self.root,self.p,runner,lambda _:None)
        self.assertTrue(result['shellRestarted'])
        self.assertEqual(self.calls.count(['omarchy','restart','shell']),1)
        self.assertFalse(any(str(s).endswith('rollback.py') for call in self.calls for s in call))

    def test_failed_bridge_keeps_launcher_during_rollback(self):
        self.confirm=False
        with self.assertRaisesRegex(AtelierError,'Resposta:'):
            activate(self.root,self.p,self.runner,lambda _:None)
        rollback=next(call for call in self.calls if any(str(s).endswith('rollback.py') for s in call))
        self.assertIn('--keep-launcher',rollback)
        self.assertEqual(self.calls.count(['omarchy','restart','shell']),2)

    def test_restart_error_is_not_reported_as_success(self):
        self.confirm=False
        def runner(args,**kw):
            if args==['omarchy','restart','shell']: raise AtelierError('session locked')
            return self.runner(args,**kw)
        with self.assertRaisesRegex(AtelierError,'session locked'):
            activate(self.root,self.p,runner,lambda _:None)
        self.assertTrue(any(str(s).endswith('rollback.py') for call in self.calls for s in call))
