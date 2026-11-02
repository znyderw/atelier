"""Filesystem services and capability-gated Omarchy adapters, independent of Qt.

Reading libraries never starts the renderer or applies a theme. Desktop mutations
require an explicit gate and the versioned bridge; the legacy plugin owns players.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import copy
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import tomllib
import uuid

IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}
POLICIES = {'Minha paleta default': {'mode':'fixed','theme':'default'},
            'Cores do wallpaper': {'mode':'auto'}, 'Manter cores atuais': {'mode':'keep'}}
RESERVED = {'default', 'wallpaper-auto', 'wallpaper-palette'}

class AtelierError(RuntimeError): pass

class Paths:
    def __init__(self, home=None, stock=None, data=None):
        self.home=Path(home or Path.home())
        self.stock=Path(stock or '/usr/share/omarchy/themes')
        self.user=self.home/'.config/omarchy/themes'
        self.legacy=self.home/'.config/omarchy/wallpaper-control.json'
        self.current=self.home/'.local/state/omarchy/current'
        self.monitors=self.home/'.local/state/omarchy/background-monitors.json'
        self.helper=self.home/'.local/share/omarchy-wallpaper-engine'
        self.plugin=self.home/'.config/omarchy/plugins/io.github.jholloway12.per-monitor-background/Background.qml'
        self.data=Path(data or self.home/'.local/share/atelier')
        self.cache=self.home/'.cache/atelier'


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return copy.deepcopy(default)
    except (ValueError, OSError) as exc:
        raise AtelierError(f'Não foi possível ler {path}: {exc}') from exc


def atomic_json(path, value):
    atomic_bytes(path, (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())


def atomic_bytes(path, value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd, name=tempfile.mkstemp(prefix='.'+path.name, dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(value); stream.flush(); os.fsync(stream.fileno())
        os.replace(name,path)
        directory=os.open(path.parent,os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        Path(name).unlink(missing_ok=True)


@contextmanager
def lock(path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        yield


def run(argv, timeout=8, env=None):
    try:
        result=subprocess.run(argv,capture_output=True,text=True,timeout=timeout,env=env,check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise AtelierError(f'Falha ao executar {argv[0]}: {exc}') from exc
    if result.returncode:
        raise AtelierError(f'{argv[0]}: {(result.stderr or result.stdout)[-1500:].strip()}')
    return result.stdout.strip()


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def toml_value(value):
    if isinstance(value,dict): return '{'+', '.join(json.dumps(str(k))+' = '+toml_value(v) for k,v in value.items())+'}'
    if isinstance(value,list): return '['+', '.join(toml_value(v) for v in value)+']'
    if isinstance(value,(str,int,float,bool)): return json.dumps(value,ensure_ascii=False,allow_nan=False)
    if hasattr(value,'isoformat'): return value.isoformat()
    raise AtelierError('Valor TOML não suportado; tema original preservado.')


def palette_toml(palette):
    text=''.join(json.dumps(str(key))+' = '+toml_value(value)+'\n' for key,value in palette.items())
    tomllib.loads(text)
    return text.encode()


class Store:
    """Versioned app state; legacy file is only changed by explicit live actions."""
    VERSION=1
    def __init__(self, paths):
        self.p=paths; self.path=paths.data/'preferences.json'

    def load(self):
        value=read_json(self.path)
        if value is None:
            legacy=self.legacy()
            return {'version':self.VERSION,'favorites':{},'legacy':legacy,'managed':{},'themes':{},'selectedMonitor':''}
        if not isinstance(value,dict) or value.get('version')!=self.VERSION:
            raise AtelierError('Versão de preferências desconhecida; arquivo preservado.')
        for key,kind in [('favorites',dict),('managed',dict),('themes',dict),('legacy',dict)]:
            if not isinstance(value.get(key),kind): raise AtelierError('Preferências inválidas; arquivo preservado.')
        return value

    def legacy(self):
        data=read_json(self.p.legacy,{'mode':'fixed','theme':'default','wallpapers':{}})
        if not isinstance(data,dict) or data.get('mode') not in ('auto','fixed','keep') or not isinstance(data.get('wallpapers',{}),dict):
            raise AtelierError('Preferências antigas inválidas; arquivo preservado.')
        return data

    def update(self, fn):
        with lock(self.p.data/'preferences.lock'):
            data=self.load(); result=fn(data)
            if self.path.exists():
                self.backup_file(self.path)
            elif self.p.legacy.exists():
                self.backup_file(self.p.legacy)
            atomic_json(self.path,data)
            return result

    def backup_file(self,path):
        dest=self.p.data/'backups'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]+'-'+Path(path).name)
        atomic_bytes(dest,Path(path).read_bytes())
        return dest

    def favorite(self,key):
        def change(data): data['favorites'][key]=not data['favorites'].get(key,False)
        self.update(change)

    def change_policy(self, key, choice, allow_desktop=False, restore=False):
        if not allow_desktop: raise AtelierError('Alteração global bloqueada até aprovação da integração.')
        # Preserve unknown fields and re-read legacy state at the point of mutation.
        with lock(self.p.data/'policy.lock'):
            self.load()  # fail before any legacy write if the versioned state is incompatible
            data=self.legacy()
            if restore:
                data.update(mode='fixed',theme='default')
                data.setdefault('wallpapers',{}).pop(key,None)
            elif key is None:
                data.update(choice)
            elif choice is None:
                data.setdefault('wallpapers',{}).pop(key,None)
            else:
                previous=data.setdefault('wallpapers',{}).get(key,{})
                data['wallpapers'][key]={**previous,**choice}
            if self.p.legacy.exists(): self.backup_file(self.p.legacy)
            atomic_json(self.p.legacy,data)
            self.update(lambda state:state.update(legacy=copy.deepcopy(data)))


def steam_libraries(paths):
    roots=[paths.home/'.local/share/Steam',paths.home/'.steam/steam',paths.home/'.steam/root']
    found=set()
    for root in roots:
        if not root.is_dir(): continue
        found.add(root.resolve())
        vdf=root/'steamapps/libraryfolders.vdf'
        if vdf.is_file():
            for match in re.finditer(r'"path"\s*"((?:\\.|[^"\\])*)"',vdf.read_text(errors='replace')):
                value=re.sub(r'\\([\\"])',r'\1',match.group(1))
                directory=Path(value)
                if directory.is_absolute() and directory.is_dir(): found.add(directory.resolve())
    return sorted(found)


def workshop_items(paths):
    items=[]; seen=set()
    for library in steam_libraries(paths):
        base=library/'steamapps/workshop/content/431960'
        for metadata in sorted(base.glob('*/project.json')):
            try:
                project=metadata.parent.resolve()
                if project in seen or not project.is_relative_to(base.resolve()) or not project.name.isdigit(): continue
                data=read_json(metadata)
                if not isinstance(data,dict): continue
                kind=str(data.get('type','')).lower()
                preview=(project/str(data.get('preview','preview.jpg'))).resolve()
                if kind not in ('scene','video') or not preview.is_relative_to(project) or not preview.is_file() or preview.suffix.lower() not in IMAGE_EXT: continue
                seen.add(project)
                items.append({'id':'workshop:'+project.name,'name':str(data.get('title',project.name))[:160],
                              'origin':'Workshop','kind':'Cena' if kind=='scene' else 'Vídeo','image':preview.as_uri(),
                              'path':str(preview),'project':str(project),'library':str(library),
                              'description':f'Workshop {project.name} · {library}','managed':False})
            except (AtelierError,OSError,TypeError): continue
    return items


class Library:
    def __init__(self,paths,store): self.p=paths; self.store=store; self._catalog=None

    def wallpapers(self):
        if self._catalog is not None: return copy.deepcopy(self._catalog)
        items=workshop_items(self.p); seen={Path(item['path']).resolve() for item in items}
        roots=[self.p.data/'wallpapers',self.p.home/'Wallpapers',self.p.home/'Pictures/Wallpapers',self.p.home/'.config/omarchy/backgrounds']
        for base in (self.p.stock,self.p.user):
            if base.is_dir(): roots.extend(d/'backgrounds' for d in base.iterdir() if d.is_dir())
        roots.append(self.p.current/'theme/backgrounds')
        state=self.store.load()
        for root in roots:
            if not root.is_dir(): continue
            for source in sorted(root.rglob('*')):
                try:
                    path=source.resolve()
                    if path in seen or not path.is_file() or path.suffix.lower() not in IMAGE_EXT: continue
                    seen.add(path)
                    key='image:'+digest(path)
                    if any(item['id']==key for item in items): continue
                    managed=state['managed'].get(key)==str(path) and path.is_relative_to((self.p.data/'wallpapers').resolve())
                    items.append({'id':key,'name':state.get('wallpaperNames',{}).get(key,path.stem),'origin':'Local','kind':'Estático','image':path.as_uri(),
                                  'path':str(path),'project':'','description':str(path),'managed':managed})
                except OSError: continue
        self._catalog=copy.deepcopy(items)
        return items

    def import_image(self, source):
        source=Path(source).resolve()
        if not source.is_file() or source.suffix.lower() not in IMAGE_EXT:
            raise AtelierError('Selecione uma imagem local suportada.')
        # Decode before copying; ffmpeg has a timeout and bounded pixel output.
        sample=run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','json',str(source)],timeout=10)
        streams=json.loads(sample).get('streams',[])
        if not streams or not streams[0].get('width'): raise AtelierError('Arquivo não contém uma imagem válida.')
        key='image:'+digest(source)
        target=self.p.data/'wallpapers'/(key[6:]+source.suffix.lower())
        if target.exists() and digest(target)!=key[6:]: raise AtelierError('Destino já existe com conteúdo diferente.')
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            with source.open('rb') as src, target.open('xb') as dest: shutil.copyfileobj(src,dest)
        def register(data):
            data['managed'][key]=str(target)
            data.setdefault('wallpaperNames',{}).setdefault(key,source.stem)
        self.store.update(register)
        self._catalog=None
        return key

    def remove(self,key):
        data=self.store.load(); value=data['managed'].get(key)
        if not value: raise AtelierError('Apenas imagens importadas pelo Atelier podem ser removidas.')
        path=Path(value)
        if path.is_symlink() or not path.resolve().is_relative_to((self.p.data/'wallpapers').resolve()):
            raise AtelierError('Caminho fora da biblioteca gerenciada.')
        if not path.is_file() or 'image:'+digest(path)!=key: raise AtelierError('Imagem alterada externamente; remoção cancelada.')
        state=read_json(self.p.monitors,{})
        if str(path) in state.get('monitors',{}).values() or path.resolve()==(self.p.current/'background').resolve():
            raise AtelierError('O wallpaper está aplicado. Troque-o antes de remover.')
        dest=self.p.data/'trash'/(uuid.uuid4().hex+'-'+path.name)
        dest.parent.mkdir(parents=True,exist_ok=True)
        path.rename(dest)  # recoverable removal; never unlink the original Steam files
        self.store.update(lambda state:state['managed'].pop(key,None))
        self._catalog=None
        return dest

    def theme_palette(self,slug):
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*',slug): raise AtelierError('Identificador de tema inválido.')
        data={}
        draft=self.p.data/'themes'/slug/'colors.toml'
        sources=[self.p.stock/slug/'colors.toml',self.p.user/slug/'colors.toml']
        if slug in self.store.load()['themes']: sources=[draft]
        for source in sources:
            if source.is_file():
                with source.open('rb') as stream: data.update(tomllib.load(stream))
        if not data: raise AtelierError('Tema sem colors.toml legível.')
        return data

    def themes(self):
        names=set(self.store.load()['themes'])
        for root in (self.p.stock,self.p.user):
            if root.is_dir(): names.update(p.name for p in root.iterdir() if p.is_dir() and (p/'colors.toml').is_file())
        result=[]
        for name in sorted(n for n in names-{'wallpaper-auto','wallpaper-palette'} if not n.startswith('atelier-applied-')):
            try:
                palette=self.theme_palette(name)
                colors=[palette.get(k,'#161616') for k in ('background','accent','foreground','green')]
                if not all(isinstance(c,str) and re.fullmatch(r'#[\da-fA-F]{6}',c) for c in colors): continue
                draft=self.store.load()['themes'].get(name)
                images=[]
                for base in (self.p.user,self.p.stock):
                    images.extend((base/name/'backgrounds').glob('*'))
                image=next((p.as_uri() for p in images if p.is_file() and p.suffix.lower() in IMAGE_EXT),'')
                result.append({'id':name,'name':draft.get('name',name) if draft else name,'origin':'Criado no app' if draft else 'Personalizado' if (self.p.user/name).is_dir() else 'Sistema',
                               'image':image,'colors':colors,'protected':not bool(draft),'palette':palette})
            except (AtelierError,OSError,ValueError): continue
        return result

    def save_theme(self,name,palette,source=None):
        name=name.strip()
        if not name or len(name)>60 or any(ord(c)<32 for c in name): raise AtelierError('Nome de tema inválido.')
        if name.casefold() in RESERVED or any(t['name'].casefold()==name.casefold() for t in self.themes()):
            raise AtelierError('Esse nome já existe ou está protegido.')
        slug='atelier-'+uuid.uuid4().hex[:12]
        atomic_bytes(self.p.data/'themes'/slug/'colors.toml',palette_toml(palette))
        self.store.update(lambda data:data['themes'].update({slug:{'name':name,'source':source}}))
        return slug

    def rename_theme(self,slug,name):
        if slug not in self.store.load()['themes'] or slug in RESERVED: raise AtelierError('Tema protegido.')
        name=name.strip()
        if not name or name.casefold() in RESERVED or any(t['name'].casefold()==name.casefold() and t['id']!=slug for t in self.themes()): raise AtelierError('Nome indisponível.')
        self.store.update(lambda data:data['themes'][slug].update(name=name))

    def remove_theme(self,slug):
        if slug not in self.store.load()['themes'] or slug in RESERVED: raise AtelierError('Tema protegido.')
        active=(self.p.current/'theme.name').read_text().strip() if (self.p.current/'theme.name').is_file() else ''
        if active==slug or (active==self.store.load().get('lastAppliedName') and slug==self.store.load().get('activeSourceTheme')) or (self.p.user/slug).exists(): raise AtelierError('Tema publicado ou ativo; preservado para recuperação.')
        source=self.p.data/'themes'/slug
        trash=self.p.data/'trash'/('theme-'+uuid.uuid4().hex)
        trash.parent.mkdir(parents=True,exist_ok=True); source.rename(trash)
        self.store.update(lambda data:data['themes'].pop(slug))


class Desktop:
    def __init__(self,paths,store,runner=run,enabled=False):
        self.p=paths; self.store=store; self.run=runner; self.enabled=enabled; self.capability_error=''

    def require(self):
        if not self.enabled: raise AtelierError('Aplicação no desktop bloqueada nesta versão de avaliação. Requer aprovação da migração.')

    def monitors(self):
        data=json.loads(self.run(['hyprctl','monitors','-j']))
        if not isinstance(data,list) or not all(isinstance(m,dict) and isinstance(m.get('name'),str) for m in data): raise AtelierError('Formato de monitores incompatível.')
        return [m for m in data if not m.get('disabled',False)]

    def capabilities(self):
        try:
            raw=self.run(['omarchy-shell','background','atelierCapabilities'])
            result=json.loads(raw)
            if isinstance(result,str): result=json.loads(result)
            if not isinstance(result,dict) or result.get('version')!=1:
                raise AtelierError('Resposta da ponte incompatível: '+raw[:300])
            self.capability_error=''
            return result
        except (AtelierError,ValueError,AttributeError) as exc:
            self.capability_error=str(exc)
            return {}

    def apply_wallpaper(self,item,monitor):
        self.require()
        if monitor not in [m['name'] for m in self.monitors()]: raise AtelierError('Monitor desconectado; atualize a lista.')
        if not self.capabilities().get('apply'): raise AtelierError('Ponte Atelier v1 não instalada; fundo atual preservado.')
        path=Path(item['path'])
        if not path.is_file(): raise AtelierError('Wallpaper não está mais disponível.')
        project=item.get('project','')
        if project and str(Path(project).resolve()) not in {i['project'] for i in workshop_items(self.p)}: raise AtelierError('Projeto Workshop não reconhecido.')
        # The bridge owns playback; this process never starts linux-wallpaperengine.
        payload=json.dumps({'version':1,'path':str(path.resolve()),'project':project},ensure_ascii=False)
        with lock(self.p.data/'desktop.lock'):
            response=json.loads(self.run(['omarchy-shell','background','atelierApply',monitor,payload]))
            if response.get('ok') is not True: raise AtelierError(response.get('error','Aplicação recusada pela shell.'))
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            state=read_json(self.p.monitors,{})
            stored=state.get('monitors',{}).get(monitor,'')
            expected_project=state.get('engine',{}).get(monitor,'')
            if stored and Path(stored).resolve()==path.resolve() and expected_project==project:
                palette_deadline=time.monotonic()+150
                while time.monotonic()<palette_deadline:
                    status=self.capabilities()
                    if not status: raise AtelierError('A shell desconectou após aceitar o wallpaper; verifique o diagnóstico.')
                    if not status.get('busy'):
                        if status.get('paletteExit',0): raise AtelierError('Wallpaper selecionado, mas a paleta falhou. Consulte os logs.')
                        return response
                    time.sleep(.15)
                raise AtelierError('Wallpaper selecionado; tempo de espera pela paleta esgotado. Consulte os logs.')
            time.sleep(.05)
        raise AtelierError('A shell aceitou a solicitação, mas não confirmou a gravação. Atualize o diagnóstico antes de repetir.')

    def apply_theme(self,name,library):
        self.require()
        if name not in {t['id'] for t in library.themes()}: raise AtelierError('Tema não encontrado.')
        # Capability probe of installed script, isolated here: public CLI has no colors-only option.
        script=Path(shutil.which('omarchy-theme-set') or '/nonexistent')
        if not script.is_file() or 'OMARCHY_THEME_SKIP_BACKGROUND' not in script.read_text():
            raise AtelierError('Aplicação só de cores incompatível com esta versão do Omarchy.')
        with lock(self.p.data/'desktop.lock'):
            target=name
            if name!='default':
                # A colors-only switch still replaces current/theme in Omarchy.
                # Preserve the complete current background gallery in an owned
                # palette carrier so current/background and monitor bases stay valid.
                target='atelier-applied-'+uuid.uuid4().hex[:12]
                dest=self.p.user/target
                dest.mkdir(parents=True,exist_ok=False)
                atomic_bytes(dest/'colors.toml',palette_toml(library.theme_palette(name)))
                style_name=name; ancestry=set()
                while style_name in self.store.load()['themes'] and style_name not in ancestry:
                    ancestry.add(style_name)
                    style_name=self.store.load()['themes'][style_name].get('source')
                    if not style_name: break
                if style_name:
                    for filename in ('icons.theme','shell.toml'):
                        source=next((base/style_name/filename for base in (self.p.user,self.p.stock) if (base/style_name/filename).is_file()),None)
                        if source: shutil.copy2(source,dest/filename)
                gallery=self.p.current/'theme/backgrounds'
                if gallery.is_dir():
                    def link_or_copy(src,dst):
                        try: return os.link(src,dst)
                        except OSError: return shutil.copy2(src,dst)
                    shutil.copytree(gallery,dest/'backgrounds',copy_function=link_or_copy)
                atomic_json(dest/'.atelier-owned.json',{'source':name,'schema':1})
            protected=self.p.user/'default/colors.toml'; before=digest(protected)
            env=dict(os.environ,OMARCHY_THEME_SKIP_BACKGROUND='1')
            self.run(['omarchy','theme','set',target],timeout=150,env=env)
            if digest(protected)!=before: raise AtelierError('Paleta default alterada externamente. Consulte o backup.')
            self.store.update(lambda data:data.update(activeSourceTheme=name,lastAppliedName=target))


def load_palette_module(paths):
    path=paths.helper/'palette.py'
    if not path.is_file(): raise AtelierError('Gerador de paletas anterior indisponível.')
    spec=importlib.util.spec_from_file_location('atelier_legacy_palette',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def diagnostics(paths,desktop):
    report={'schema':1,'desktopEnabled':desktop.enabled,'commands':{},'issues':[], 'adapters':{},
            'python':__import__('sys').version.split()[0],'pysideAvailable':importlib.util.find_spec('PySide6') is not None}
    if not report['pysideAvailable']: report['issues'].append('PySide6 indisponível neste Python.')
    for command in ['omarchy','omarchy-shell','hyprctl','qs','linux-wallpaperengine','ffmpeg','ffprobe']:
        report['commands'][command]=shutil.which(command)
        if not report['commands'][command]: report['issues'].append('Ausente: '+command)
    for package in ['omarchy','hyprland','quickshell','linux-wallpaperengine-git']:
        try: report.setdefault('versions',{})[package]=desktop.run(['pacman','-Q',package])
        except AtelierError as exc: report['issues'].append(str(exc))
    try: report['monitors']=desktop.monitors()
    except (AtelierError,ValueError) as exc: report['monitors']=[]; report['issues'].append('Sessão Hyprland: '+str(exc))
    try:
        help_text=desktop.run(['linux-wallpaperengine','--help'])
        report['adapters']['rendererArguments']=all(arg in help_text for arg in ['--screen-root','--bg','--fps','--assets-dir','--scaling','--disable-mouse','--silent','--layer','--no-fullscreen-pause'])
    except AtelierError:
        report['adapters']['rendererArguments']=False
    if not report['adapters']['rendererArguments']: report['issues'].append('Argumentos do renderizador indisponíveis ou incompatíveis.')
    report['adapters']['bridge']=desktop.capabilities()
    if not report['adapters']['bridge']: report['issues'].append('Ponte Atelier v1 ainda não ativada.')
    script=Path(shutil.which('omarchy-theme-set') or '/nonexistent')
    report['adapters']['colorsOnly']=script.is_file() and 'OMARCHY_THEME_SKIP_BACKGROUND' in script.read_text()
    report['fingerprints']={}
    for source in [paths.plugin,paths.helper/'picker.py',paths.helper/'control.py',paths.helper/'palette.py',script]:
        if source.is_file(): report['fingerprints'][str(source)]=digest(source)
    report['directories']={str(path):{'exists':path.exists(),'readable':os.access(path,os.R_OK),
                                     'writable':os.access(path if path.exists() else path.parent,os.W_OK)}
                           for path in [paths.user,paths.stock,paths.helper,paths.data]}
    report['logs']={}
    logs=paths.home/'.local/state/omarchy/wallpaper-engine'
    for source in sorted(logs.glob('*.log'))[-6:]:
        with source.open('rb') as stream:
            stream.seek(max(0,source.stat().st_size-4096))
            report['logs'][source.name]=stream.read(4096).decode(errors='replace')
    baseline=read_json(paths.data/'compatibility-baseline.json',{})
    report['changedSinceBaseline']=bool(baseline and (baseline.get('fingerprints')!=report['fingerprints'] or baseline.get('versions')!=report.get('versions')))
    if report['changedSinceBaseline']: report['issues'].append('Arquivos de integração mudaram desde a baseline; revise a compatibilidade.')
    return report
