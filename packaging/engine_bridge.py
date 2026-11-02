#!/usr/bin/env python3
"""Compatibility entry point: preserve the legacy owner and add Steam libraries.

Called by the existing plugin, never by the GUI. The plugin serializes player
lifecycle for each monitor. A process lock prevents two bridge renderers for the
same monitor. No Workshop files are modified.
"""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atelier.core import Paths, steam_libraries, workshop_items, AtelierError


def main():
    p=Paths(); source=p.helper/'picker.py'
    spec=importlib.util.spec_from_file_location('atelier_old_picker',source)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    # Legacy control imports palette by its sibling name.
    sys.path.insert(0,str(p.helper))
    action=sys.argv[1] if len(sys.argv)>1 else ''
    if action=='render' and len(sys.argv)==4:
        project=Path(sys.argv[2]).resolve(); screen=sys.argv[3]
        if not re.fullmatch(r'[A-Za-z0-9_.:-]+',screen): raise AtelierError('Monitor inválido.')
        match=next((item for item in workshop_items(p) if Path(item['project'])==project),None)
        if not match: raise AtelierError('Projeto fora das bibliotecas Steam reconhecidas.')
        lockdir=p.home/'.local/state/atelier/renderers'; lockdir.mkdir(parents=True,exist_ok=True)
        handle=(lockdir/(screen+'.lock')).open('a')
        try: fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise AtelierError('Já existe um renderizador Atelier neste monitor.')
        os.set_inheritable(handle.fileno(),True)
        # Retain the handle across execv in the unchanged legacy render function.
        libraries=steam_libraries(p)
        assets=next((library/'steamapps/common/wallpaper_engine/assets' for library in libraries
                     if (library/'steamapps/common/wallpaper_engine/assets').is_dir()),None)
        if not assets: raise AtelierError('Assets do Wallpaper Engine não encontrados.')
        module.STEAM=Path(match['library'])/'steamapps'
        # Legacy function uses STEAM for both project validation and assets; implement
        # identical args here when assets are in a different library.
        renderer=__import__('shutil').which('linux-wallpaperengine')
        if not renderer: raise AtelierError('linux-wallpaperengine ausente.')
        log=p.home/'.local/state/omarchy/wallpaper-engine'/(screen+'.log'); log.parent.mkdir(parents=True,exist_ok=True)
        with log.open('ab',buffering=0) as stream:
            os.dup2(stream.fileno(),1); os.dup2(stream.fileno(),2)
        os.execv(renderer,[renderer,'--silent','--fps','30','--disable-mouse','--layer','background',
                           '--no-fullscreen-pause','--assets-dir',str(assets),'--scaling','fill',
                           '--screen-root',screen,'--bg',str(project)])
    elif action=='pick' and len(sys.argv) in (2,3):
        module.pick(sys.argv[2] if len(sys.argv)==3 else '')
    elif action=='palette' and len(sys.argv)==3:
        from atelier.service import Service
        from atelier.core import Store, Desktop, digest
        path=Path(sys.argv[2]).resolve()
        key=next((i['id'] for i in workshop_items(p) if Path(i['path']).resolve()==path),'image:'+digest(path))
        service=Service(p,Desktop(p,Store(p),enabled=True))
        service.apply_policy({'id':key,'path':str(path)})
    else:
        raise AtelierError('Operação de integração inválida.')

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(str(exc),file=sys.stderr); raise SystemExit(1)
