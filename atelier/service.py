"""Application operations, usable from Qt or the command-line validator."""
import json
from pathlib import Path
import re
from .core import (AtelierError, Paths, Store, Library, Desktop, POLICIES, read_json,
                   atomic_json, diagnostics, digest, load_palette_module)

class Service:
    def __init__(self,paths=None,desktop=None):
        self.p=paths or Paths(); self.store=Store(self.p); self.library=Library(self.p,self.store)
        self.desktop=desktop or Desktop(self.p,self.store)
        self.palette={}; self.original={}; self.source_theme='default'
        self.report={}; self.last_error=''

    def refresh(self):
        self.library._catalog=None
        self.report=diagnostics(self.p,self.desktop)
        return self.snapshot()

    def snapshot(self):
        data=self.store.load(); walls=self.library.wallpapers(); themes=self.library.themes()
        if not self.palette and themes:
            selected=next((t for t in themes if t['id']=='default'),themes[0])
            self.load_theme(selected['id'])
        monitors=self.report.get('monitors',[])
        selected=data.get('selectedMonitor','')
        index=next((i for i,m in enumerate(monitors) if m['name']==selected),(-1 if selected or not monitors else next((i for i,m in enumerate(monitors) if m.get('focused')),0)))
        saved=read_json(self.p.monitors,{})
        base=str((self.p.current/'background').resolve())
        applied={}
        for i,m in enumerate(monitors):
            path=saved.get('monitors',{}).get(m['name'],base) if saved.get('base')==base else base
            applied[str(i)]=next((w['id'] for w in walls if Path(w['path']).resolve()==Path(path).resolve()),'')
        legacy=self.store.legacy()
        def label(rule):
            if rule.get('mode')=='auto': return 'Cores do wallpaper'
            if rule.get('mode')=='keep': return 'Manter cores atuais'
            if rule.get('theme','default')=='default': return 'Minha paleta default'
            return 'Paleta: '+rule['theme']
        active=(self.p.current/'theme.name').read_text().strip() if (self.p.current/'theme.name').is_file() else ''
        if active==data.get('lastAppliedName'): active=data.get('activeSourceTheme',active)
        return {'wallpapers':walls,'themes':themes,'monitors':[m['name'] for m in monitors],
                'monitorIndex':index,'applied':applied,'activeTheme':active,
                'globalPolicy':label(legacy),'exceptions':{k:label(v) for k,v in legacy.get('wallpapers',{}).items()},
                'favorites':data['favorites'],'original':self.editable(self.original),'palette':self.editable(self.palette),
                'dirty':self.palette!=self.original,'diagnostics':json.dumps(self.report,ensure_ascii=False,indent=2),
                'desktopEnabled':self.desktop.enabled,'sourceTheme':self.source_theme}

    @staticmethod
    def editable(palette):
        return {k:v for k,v in palette.items() if isinstance(v,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',v)}

    def load_theme(self,slug):
        self.original=self.library.theme_palette(slug); self.palette=self.original.copy(); self.source_theme=slug

    def item(self,key):
        return next((i for i in self.library.wallpapers() if i['id']==key),None) or self.missing()

    @staticmethod
    def missing(): raise AtelierError('Wallpaper não encontrado. Atualize a biblioteca.')

    def dispatch(self,action,args):
        if action=='refresh': return self.refresh()
        if action=='favorite': self.store.favorite(args['id'])
        elif action=='monitor': self.store.update(lambda d:d.update(selectedMonitor=args['name']))
        elif action=='import': self.library.import_image(args['path'])
        elif action=='remove': self.library.remove(args['id'])
        elif action=='loadTheme': self.load_theme(args['id'])
        elif action=='editColor':
            if args['key'] not in self.editable(self.palette) or not re.fullmatch(r'#[0-9a-fA-F]{6}',args['value']): raise AtelierError('Cor inválida.')
            self.palette[args['key']]=args['value']
        elif action=='revert': self.palette=self.original.copy()
        elif action=='extract':
            item=self.item(args['id'])
            self.palette=load_palette_module(self.p).generate(item['path'])
        elif action=='saveTheme':
            self.source_theme=self.library.save_theme(args['name'],self.palette,self.source_theme)
            self.original=self.palette.copy()
        elif action=='duplicateTheme': self.library.save_theme(args['name'],self.library.theme_palette(args['id']),args['id'])
        elif action=='renameTheme': self.library.rename_theme(args['id'],args['name'])
        elif action=='removeTheme': self.library.remove_theme(args['id'])
        elif action=='wallpaper':
            self.desktop.apply_wallpaper(self.item(args['id']),args['monitor'])
        elif action=='theme':
            self.desktop.apply_theme(args['id'],self.library)
            self.store.change_policy(None,{'mode':'fixed','theme':args['id']},allow_desktop=True)
        elif action=='palette':
            if self.palette!=self.original: raise AtelierError('Salve a paleta como um novo tema antes de aplicar.')
            self.desktop.apply_theme(self.source_theme,self.library)
        elif action in ('exception','global','restore'):
            self.desktop.require()
            key=args.get('id')
            value=args.get('value','')
            choice=None if value=='Seguir padrão' else POLICIES.get(value)
            if value.startswith('Paleta: '):
                slug=value[8:]
                if slug not in {t['id'] for t in self.library.themes()}: raise AtelierError('Tema não disponível.')
                choice={'mode':'fixed','theme':slug}
            if action!='restore' and args.get('value')!='Seguir padrão' and choice is None: raise AtelierError('Política inválida.')
            if action=='global': key=None
            self.store.change_policy(key,choice,allow_desktop=True,restore=action=='restore')
            if action=='restore': self.desktop.apply_theme('default',self.library)
            elif key:
                # The old generator and theme adapter preserve the old preference semantics.
                self.apply_policy(self.item(key))
            else:
                # Apply the global policy to the current image on the selected monitor.
                monitor=args.get('monitor','')
                saved=read_json(self.p.monitors,{})
                base=str((self.p.current/'background').resolve())
                path=saved.get('monitors',{}).get(monitor,base) if saved.get('base')==base else base
                current=next((w for w in self.library.wallpapers() if Path(w['path']).resolve()==Path(path).resolve()),{'id':'image:'+digest(path),'path':path})
                self.apply_policy(current)
        elif action=='baseline': atomic_json(self.p.data/'compatibility-baseline.json',self.report)
        else: raise AtelierError('Operação desconhecida: '+action)
        if action in ('wallpaper','theme','palette','exception','global','restore'):
            self.report=diagnostics(self.p,self.desktop)
        return self.snapshot()

    def apply_policy(self,item):
        self.desktop.require()
        data=self.store.legacy(); policy=data.get('wallpapers',{}).get(item['id'],data)
        if policy['mode']=='auto':
            image_hash=digest(item['path'])
            state=self.store.load()
            slug=state.get('paletteCache',{}).get(image_hash)
            if slug not in state['themes']:
                colors=load_palette_module(self.p).generate(item['path'])
                slug=self.library.save_theme('Paleta '+__import__('uuid').uuid4().hex[:8],colors)
                self.store.update(lambda d:d.setdefault('paletteCache',{}).update({image_hash:slug}))
            self.desktop.apply_theme(slug,self.library)
        elif policy['mode']=='fixed': self.desktop.apply_theme(policy.get('theme','default'),self.library)
