import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from atelier.core import *
from atelier.service import Service

class Services(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name); self.p=Paths(root/'home',root/'stock',root/'data')
        self.p.home.mkdir(); self.store=Store(self.p); self.lib=Library(self.p,self.store)
        self.default=self.p.user/'default/colors.toml'
        self.default.parent.mkdir(parents=True)
        self.default.write_text('mode = "dark"\nbackground="#161e2a"\nforeground="#EEEFEE"\naccent="#757c96"\ngreen="#a7c4da"\nunknown="preserve me"\n')
        atomic_json(self.p.legacy,{'mode':'fixed','theme':'default','custom':'preserved','wallpapers':{'workshop:123':{'mode':'auto','label':'Old'}}})

    def image(self,name='local.png',content=b'example'):
        p=self.p.home/'Wallpapers'/name; p.parent.mkdir(exist_ok=True); p.write_bytes(content); return p

    def workshop(self,library,id='123',kind='scene',preview='preview.jpg'):
        project=library/'steamapps/workshop/content/431960'/id; project.mkdir(parents=True)
        (project/'preview.jpg').write_bytes(b'preview')
        atomic_json(project/'project.json',{'type':kind,'title':'A scene','preview':preview})
        return project

    def test_migration_lossless_restart(self):
        old=self.p.legacy.read_bytes(); state=self.store.load()
        self.assertEqual(state['legacy']['custom'],'preserved')
        self.store.favorite('workshop:123')
        new=Store(self.p).load()
        self.assertTrue(new['favorites']['workshop:123']); self.assertEqual(new['legacy']['wallpapers']['workshop:123']['label'],'Old')
        self.assertEqual(old,self.p.legacy.read_bytes())
        self.assertTrue(list((self.p.data/'backups').glob('*')))

    def test_future_version_preserved(self):
        atomic_json(self.store.path,{'version':99}); before=self.store.path.read_bytes()
        with self.assertRaises(AtelierError): self.store.favorite('x')
        self.assertEqual(before,self.store.path.read_bytes())

    def test_corrupt_preferences_preserved(self):
        atomic_bytes(self.store.path,b'{broken')
        with self.assertRaises(AtelierError): self.store.load()
        self.assertEqual(self.store.path.read_bytes(),b'{broken')

    def test_invalid_legacy_not_silently_replaced(self):
        atomic_json(self.p.legacy,{'mode':'unknown'})
        with self.assertRaises(AtelierError): self.store.load()

    def test_two_steam_libraries(self):
        primary=self.p.home/'.local/share/Steam'; secondary=self.p.home/'Extra Steam'
        self.workshop(primary); self.workshop(secondary,'456','video')
        (primary/'steamapps/libraryfolders.vdf').write_text('"libraryfolders" {"0" {"path" "'+str(primary)+'"} "1" {"path" "'+str(secondary)+'"}}')
        self.assertEqual({i['id'] for i in self.lib.wallpapers()},{'workshop:123','workshop:456'})

    def test_workshop_traversal_and_unknown_type_skipped(self):
        primary=self.p.home/'.local/share/Steam'
        self.workshop(primary,preview='../../../../outside.jpg')
        self.workshop(primary,'456','web')
        self.assertEqual(workshop_items(self.p),[])

    def test_discovery_deduplicates_images(self):
        self.image(); self.image('copy.png')
        self.assertEqual(len(self.lib.wallpapers()),1)

    def test_import_and_safe_removal(self):
        source=self.image(); before=source.read_bytes()
        with patch('atelier.core.run',return_value='{"streams":[{"width":20,"height":20}]}'):
            key=self.lib.import_image(source)
        managed=Path(self.store.load()['managed'][key]); self.assertTrue(managed.exists())
        trash=self.lib.remove(key)
        self.assertTrue(trash.exists()); self.assertFalse(managed.exists()); self.assertEqual(source.read_bytes(),before)

    def test_cannot_remove_workshop_or_external(self):
        with self.assertRaises(AtelierError): self.lib.remove('workshop:123')
        source=self.image(); key='image:'+digest(source)
        self.store.update(lambda d:d['managed'].update({key:str(source)}))
        with self.assertRaises(AtelierError): self.lib.remove(key)
        self.assertTrue(source.exists())

    def test_applied_image_preserved(self):
        source=self.image()
        with patch('atelier.core.run',return_value='{"streams":[{"width":20}]}'): key=self.lib.import_image(source)
        path=self.store.load()['managed'][key]
        atomic_json(self.p.monitors,{'monitors':{'DP-1':path}})
        with self.assertRaises(AtelierError): self.lib.remove(key)

    def test_theme_copy_preserves_unknown_and_default(self):
        before=self.default.read_bytes()
        palette=self.lib.theme_palette('default'); palette['accent']='#ffffff'
        slug=self.lib.save_theme('New theme',palette)
        self.assertEqual(self.lib.theme_palette(slug)['unknown'],'preserve me')
        self.assertEqual(self.default.read_bytes(),before)
        self.assertEqual(self.lib.theme_palette(slug)['accent'],'#ffffff')

    def test_reserved_names_and_slug_escape(self):
        for name in ['Default','wallpaper-auto','']:
            with self.assertRaises(AtelierError): self.lib.save_theme(name,{'background':'#000000'})
        with self.assertRaises(AtelierError): self.lib.theme_palette('../default')
        with self.assertRaises(AtelierError): self.lib.remove_theme('default')

    def test_overlay_combines_stock_user(self):
        stock=self.p.stock/'overlay/colors.toml'; stock.parent.mkdir(parents=True); stock.write_text('accent="#aaaaaa"\nbackground="#000000"\n')
        user=self.p.user/'overlay/colors.toml'; user.parent.mkdir(); user.write_text('accent="#bbbbbb"\n')
        self.assertEqual(self.lib.theme_palette('overlay')['background'],'#000000')
        self.assertEqual(self.lib.theme_palette('overlay')['accent'],'#bbbbbb')

    def test_theme_rename_delete_only_managed(self):
        slug=self.lib.save_theme('New',self.lib.theme_palette('default'))
        self.lib.rename_theme(slug,'Renamed'); self.assertEqual(self.store.load()['themes'][slug]['name'],'Renamed')
        self.lib.remove_theme(slug); self.assertNotIn(slug,self.store.load()['themes'])
        with self.assertRaises(AtelierError): self.lib.rename_theme('default','Altered')

    def test_policy_is_gated(self):
        before=self.p.legacy.read_bytes()
        with self.assertRaises(AtelierError): self.store.change_policy(None,{'mode':'auto'})
        self.assertEqual(before,self.p.legacy.read_bytes())

    def test_restore_only_clears_target(self):
        self.store.change_policy('workshop:other',{'mode':'keep'},True)
        self.store.change_policy('workshop:123',None,True,restore=True)
        data=self.store.legacy(); self.assertEqual(data['theme'],'default')
        self.assertNotIn('workshop:123',data['wallpapers']); self.assertIn('workshop:other',data['wallpapers']); self.assertEqual(data['custom'],'preserved')

    def fake_run(self,argv,**kwargs):
        if argv[0]=='hyprctl': return '[{"name":"DP-1"}]'
        if argv[-1]=='atelierCapabilities': return '{"version":1,"apply":true}'
        if 'atelierApply' in argv:
            choice=json.loads(argv[-1]); monitor=argv[-2]
            atomic_json(self.p.monitors,{'monitors':{monitor:choice['path']},'engine':{monitor:choice['project']}})
            return '{"ok":true}'
        return ''

    def test_wallpaper_uses_bridge_no_renderer(self):
        calls=[]
        def runner(argv,**kwargs): calls.append(argv); return self.fake_run(argv,**kwargs)
        desktop=Desktop(self.p,self.store,runner,True)
        self.image(); desktop.apply_wallpaper(self.lib.wallpapers()[0],'DP-1')
        self.assertEqual(len([c for c in calls if c[:3]==['omarchy-shell','background','atelierApply']]),1)
        self.assertFalse(any(c[0]=='linux-wallpaperengine' for c in calls))

    def test_detached_monitor_fails_before_apply(self):
        desktop=Desktop(self.p,self.store,self.fake_run,True); self.image()
        with self.assertRaisesRegex(AtelierError,'desconectado'): desktop.apply_wallpaper(self.lib.wallpapers()[0],'HDMI-1')

    def test_missing_bridge_gates_mutation(self):
        def runner(argv,**kwargs): return '[{"name":"DP-1"}]' if argv[0]=='hyprctl' else '{"version":2}'
        desktop=Desktop(self.p,self.store,runner,True); self.image()
        with self.assertRaisesRegex(AtelierError,'Ponte'): desktop.apply_wallpaper(self.lib.wallpapers()[0],'DP-1')

    def test_failed_shell_response_visible(self):
        def runner(argv,**kwargs):
            if 'atelierApply' in argv: return '{"ok":false,"error":"busy"}'
            return self.fake_run(argv,**kwargs)
        self.image()
        with self.assertRaisesRegex(AtelierError,'busy'): Desktop(self.p,self.store,runner,True).apply_wallpaper(self.lib.wallpapers()[0],'DP-1')

    def test_invalid_monitor_format(self):
        with self.assertRaises(AtelierError): Desktop(self.p,self.store,lambda a:'{}').monitors()

    def test_desktop_disabled_allows_local_editor(self):
        service=Service(self.p)
        service.load_theme('default'); service.palette['accent']='#abcdef'
        with patch('atelier.service.diagnostics',return_value={}): service.dispatch('saveTheme',{'name':'Safe draft'})
        with self.assertRaises(AtelierError): service.dispatch('theme',{'id':'default'})
        self.assertEqual(self.lib.theme_palette('default')['accent'],'#757c96')

    def test_editor_bad_color_rejected(self):
        service=Service(self.p); service.load_theme('default')
        with self.assertRaises(AtelierError): service.dispatch('editColor',{'key':'accent','value':'red'})

    def test_process_failures_are_controlled(self):
        with patch('subprocess.run',side_effect=subprocess.TimeoutExpired('x',1)):
            with self.assertRaises(AtelierError): run(['x'])
        with patch('subprocess.run',return_value=subprocess.CompletedProcess(['x'],1,'','failure')):
            with self.assertRaisesRegex(AtelierError,'failure'): run(['x'])

    def test_theme_apply_colors_only_default_unchanged(self):
        source=self.p.home/'omarchy-theme-set'; source.write_text('OMARCHY_THEME_SKIP_BACKGROUND')
        calls=[]
        def runner(argv,**kw): calls.append((argv,kw)); return ''
        with patch('atelier.core.shutil.which',return_value=str(source)):
            Desktop(self.p,self.store,runner,True).apply_theme('default',self.lib)
        self.assertEqual(calls[-1][0],['omarchy','theme','set','default'])
        self.assertEqual(calls[-1][1]['env']['OMARCHY_THEME_SKIP_BACKGROUND'],'1')

    def test_theme_apply_missing_capability(self):
        source=self.p.home/'old-script'; source.write_text('unsupported')
        with patch('atelier.core.shutil.which',return_value=str(source)):
            with self.assertRaises(AtelierError): Desktop(self.p,self.store,self.fake_run,True).apply_theme('default',self.lib)

if __name__=='__main__': unittest.main()

class AdditionalServices(unittest.TestCase):
    setUp=Services.setUp
    image=Services.image
    workshop=Services.workshop
    fake_run=Services.fake_run
    def test_unknown_toml_structures_roundtrip(self):
        palette=self.lib.theme_palette('default')
        palette['future']={'unknown-array':[1,'two',True],'nested':{'x':'unchanged'}}
        slug=self.lib.save_theme('Future fields',palette)
        self.assertEqual(self.lib.theme_palette(slug)['future'],palette['future'])

    def test_colors_carrier_preserves_gallery(self):
        palette=self.lib.theme_palette('default'); slug=self.lib.save_theme('Draft',palette)
        image=self.p.current/'theme/backgrounds/keep.png'; image.parent.mkdir(parents=True); image.write_bytes(b'keep')
        script=self.p.home/'script'; script.write_text('OMARCHY_THEME_SKIP_BACKGROUND')
        calls=[]
        with patch('atelier.core.shutil.which',return_value=str(script)):
            Desktop(self.p,self.store,lambda argv,**kw:calls.append(argv) or '',True).apply_theme(slug,self.lib)
        target=calls[-1][-1]
        self.assertTrue(target.startswith('atelier-applied-'))
        self.assertEqual((self.p.user/target/'backgrounds/keep.png').read_bytes(),b'keep')
        self.assertEqual(self.store.load()['activeSourceTheme'],slug)
        self.assertEqual(self.lib.theme_palette('default')['accent'],'#757c96')

    def test_compatibility_diagnostic_read_only(self):
        def runner(argv,**kw):
            if argv[0]=='hyprctl': raise AtelierError('Session offline')
            if argv[0]=='pacman': return argv[-1]+' test-version'
            raise AtelierError('Bridge missing')
        before=self.p.legacy.read_bytes()
        report=diagnostics(self.p,Desktop(self.p,self.store,runner))
        self.assertTrue(report['issues']); self.assertFalse(self.p.data.exists())
        self.assertEqual(before,self.p.legacy.read_bytes())

    def test_baseline_change_detected(self):
        atomic_json(self.p.data/'compatibility-baseline.json',{'fingerprints':{'old':'sha'}})
        report=diagnostics(self.p,Desktop(self.p,self.store,self.fake_run))
        self.assertTrue(report['changedSinceBaseline'])

    def test_policy_other_theme_validated(self):
        service=Service(self.p,Desktop(self.p,self.store,self.fake_run,True))
        with self.assertRaises(AtelierError): service.dispatch('exception',{'id':'workshop:123','value':'Paleta: ../escape'})
        self.assertEqual(self.store.legacy()['wallpapers']['workshop:123']['mode'],'auto')

    def test_thumbnail_cache(self):
        from atelier.thumbnails import ThumbnailCache
        source=self.image()
        cache=ThumbnailCache(self.p.cache/'thumbnails')
        result=subprocess.CompletedProcess([],0,b'\x89PNG\r\n\x1a\nDATA',b'')
        with patch('atelier.thumbnails.subprocess.run',return_value=result) as mock:
            first=cache.get(source); second=cache.get(source)
            self.assertEqual(first,second); self.assertEqual(mock.call_count,1)
            source.write_bytes(b'changed')
            third=cache.get(source); self.assertNotEqual(first,third); self.assertEqual(mock.call_count,2)

    def test_thumbnail_failure_does_not_replace_original(self):
        from atelier.thumbnails import ThumbnailCache
        source=self.image(); before=source.read_bytes()
        with patch('atelier.thumbnails.subprocess.run',side_effect=subprocess.TimeoutExpired('ffmpeg',1)):
            with self.assertRaises(AtelierError): ThumbnailCache(self.p.cache).get(source)
        self.assertEqual(before,source.read_bytes())

    def test_migration_candidate_is_separate_and_fails_closed(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
        from prepare_migration import prepare
        source=Path.home()/'.config/omarchy/plugins/io.github.jholloway12.per-monitor-background/Background.qml'
        if not source.is_file(): self.skipTest('Installed plugin fixture not available')
        before=source.read_bytes(); candidate=prepare(source.read_text())
        self.assertNotIn('acceptedButtons: Qt.LeftButton | Qt.RightButton',candidate)
        self.assertIn('function atelierApply',candidate)
        self.assertIn('--monitor',candidate)
        self.assertEqual(before,source.read_bytes())
        with self.assertRaises(RuntimeError): prepare('unknown plugin')

    def test_backup_verified(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
        from backup import snapshot
        self.image()
        destination=Path(self.tmp.name)/'archive'
        snapshot(self.p.home,destination,['Wallpapers','.config/omarchy/themes'])
        self.assertTrue((destination/'VALIDATED.txt').exists())
        metadata=json.loads((destination/'manifest.json').read_text())
        self.assertEqual(metadata['files']['.config/omarchy/themes/default/colors.toml'],digest(self.default))

class Packaging(unittest.TestCase):
    setUp=Services.setUp
    def test_install_plan_apply_and_guarded_rollback_in_temporary_home(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
        import install,rollback
        root=Path(self.tmp.name)/'application'; stage=root/'packaging';stage.mkdir(parents=True)
        plugin=self.p.plugin;plugin.parent.mkdir(parents=True);plugin.write_text('original plugin')
        candidate=stage/'Background.qml';candidate.write_text('candidate plugin')
        (stage/'atelier.desktop').write_text('[Desktop Entry]\nName=Atelier\n')
        launcher=self.p.home/'.local/share/applications/atelier.desktop'
        atomic_json(stage/'migration-plan.json',{'plugin':str(plugin),'before':digest(plugin),'candidate':str(candidate),'candidateHash':digest(candidate),'launcher':str(launcher)})
        with patch.object(install,'ROOT',root),patch.object(install,'run',return_value=''),patch('pathlib.Path.home',return_value=self.p.home):
            with patch('sys.argv',['install.py']): install.main()
            self.assertEqual(plugin.read_text(),'original plugin');self.assertFalse(launcher.exists())
            with patch('sys.argv',['install.py','--apply']):
                with self.assertRaises(RuntimeError): install.main()
            with patch('sys.argv',['install.py','--apply','--graphical-tests-passed']): install.main()
            self.assertEqual(plugin.read_text(),'candidate plugin');self.assertTrue(launcher.exists())
            backup=next((self.p.home/'configs/backups').glob('atelier-migration-*'))
            with patch('sys.argv',['rollback.py',str(backup)]): rollback.main()
            self.assertEqual(plugin.read_text(),'candidate plugin')
            plugin.write_text('user change')
            with patch('sys.argv',['rollback.py',str(backup),'--apply']):
                with self.assertRaises(RuntimeError): rollback.main()
            plugin.write_text('candidate plugin')
            with patch('sys.argv',['rollback.py',str(backup),'--apply']): rollback.main()
            self.assertEqual(plugin.read_text(),'original plugin');self.assertFalse(launcher.exists())
        self.assertEqual(self.lib.theme_palette('default')['accent'],'#757c96')

class Regression(unittest.TestCase):
    setUp=Services.setUp
    image=Services.image
    def test_imported_copy_is_the_managed_catalog_entry(self):
        source=self.image('Named wallpaper.png')
        self.lib.wallpapers()  # populate discovery cache before import
        with patch('atelier.core.run',return_value='{"streams":[{"width":20}]}'): key=self.lib.import_image(source)
        item=next(i for i in self.lib.wallpapers() if i['id']==key)
        self.assertTrue(item['managed']);self.assertEqual(item['name'],'Named wallpaper')

    def test_disconnected_saved_monitor_requires_new_selection(self):
        self.store.update(lambda data:data.update(selectedMonitor='disconnected'))
        service=Service(self.p);service.report={'monitors':[{'name':'DP-1'}]}
        self.assertEqual(service.snapshot()['monitorIndex'],-1)

    def test_concurrent_favorites_preserve_all_keys(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda i:Store(self.p).favorite(str(i)),range(12)))
        self.assertEqual(len(self.store.load()['favorites']),12)

class PolicyRegression(unittest.TestCase):
    setUp=Services.setUp
    workshop=Services.workshop
    fake_run=Services.fake_run
    def test_global_change_preserves_workshop_exception_precedence(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        project=self.workshop(self.p.home/'.local/share/Steam')
        self.p.current.mkdir(parents=True)
        (self.p.current/'background').symlink_to(project/'preview.jpg')
        service=Service(self.p,Desktop(self.p,self.store,self.fake_run,True))
        generator=Mock(return_value=self.lib.theme_palette('default'))
        with patch('atelier.service.load_palette_module',return_value=SimpleNamespace(generate=generator)),patch.object(service.desktop,'apply_theme') as apply:
            service.dispatch('global',{'value':'Manter cores atuais','monitor':'DP-1'})
        self.assertEqual(self.store.legacy()['mode'],'keep')
        self.assertEqual(self.store.legacy()['wallpapers']['workshop:123']['mode'],'auto')
        generator.assert_called_once()
        apply.assert_called_once()

class CapabilityResponses(unittest.TestCase):
    def test_encoded_response_and_failure_detail(self):
        from atelier.core import Desktop,Paths,Store
        p=Paths()
        raw=json.dumps(json.dumps({'version':1,'apply':True}))
        desktop=Desktop(p,Store(p),lambda argv:raw)
        self.assertTrue(desktop.capabilities()['apply'])
        def missing(argv): raise AtelierError('Function not found.')
        desktop.run=missing
        self.assertEqual(desktop.capabilities(),{})
        self.assertIn('Function not found.',desktop.capability_error)
