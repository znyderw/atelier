#!/usr/bin/env python3
"""First-run activation from the user's graphical session, with verified rollback.

This is also the desktop launcher entry point. Already active installations simply
open the application. No package installation or Omarchy update is performed.
"""
import json
import html
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from atelier.core import AtelierError, Paths, Store, Desktop, atomic_json, run, digest, lock


def activate(root=ROOT,paths=None,runner=run,sleep=time.sleep):
    paths=paths or Paths()
    with lock(paths.data/'activation.lock'):
        return _activate(root,paths,runner,sleep)


def _activate(root,paths,runner,sleep):
    desktop=Desktop(paths,Store(paths),runner=runner)
    monitors=desktop.monitors()
    if not monitors: raise AtelierError('Nenhum monitor ativo na sessão Hyprland.')
    if desktop.capabilities().get('apply'):
        return {'alreadyActive':True,'monitors':[m['name'] for m in monitors]}
    plan=json.loads((root/'packaging/migration-plan.json').read_text())
    if digest(paths.plugin)!=plan['before']:
        raise AtelierError('O plugin foi alterado depois da preparação. Integração preservada; gere e revise um novo plano.')
    before=digest(paths.user/'default/colors.toml')
    # Installer repeats runtime tests without allowing skips and makes its own backup.
    output=runner([sys.executable,str(root/'tools/install.py'),'--apply','--graphical-tests-passed'],timeout=180)
    backup_line=next((line.split('Backup:',1)[1].strip() for line in output.splitlines() if line.startswith('Migração instalada. Backup:')),None)
    if not backup_line:
        raise AtelierError('Instalador não confirmou o backup. Consulte os logs antes de repetir.')
    restarted=False
    try:
        # Local QML components can remain cached after a plugin rescan. Try
        # hot reload first, then one official restart that waits for the old
        # shell/players to exit and respects the session lock.
        ready=False
        for attempt in range(12):
            if desktop.capabilities().get('apply'):
                ready=True; break
            if attempt==6: runner(['omarchy-shell','shell','rescanPlugins'])
            sleep(.25)
        if not ready:
            print('Atelier: reiniciando a shell para registrar a integração…',flush=True)
            restarted=True
            runner(['omarchy','restart','shell'],timeout=150)
            for _ in range(60):
                if desktop.capabilities().get('apply'):
                    ready=True; break
                sleep(.25)
        if not ready:
            raise AtelierError('A shell não confirmou a ponte Atelier após reiniciar. Resposta: '+desktop.capability_error)
        if digest(paths.user/'default/colors.toml')!=before:
            raise AtelierError('O default mudou durante a ativação. Consulte o backup; nenhuma restauração automática da paleta foi feita.')
        result={'alreadyActive':False,'backup':backup_line,'monitors':[m['name'] for m in monitors],'shellRestarted':restarted}
        atomic_json(paths.data/'activation.json',result)
        return result
    except Exception as activation_error:
        # Preserve the launcher during automatic rollback so the app remains
        # discoverable. Manual rollback can still remove it explicitly.
        try:
            runner([sys.executable,str(root/'tools/rollback.py'),backup_line,'--apply','--keep-launcher'],timeout=30)
            if restarted:
                runner(['omarchy','restart','shell'],timeout=150)
        except Exception as rollback_error:
            raise AtelierError(str(activation_error)+'; recuperação requer revisão: '+str(rollback_error)) from activation_error
        raise


def main():
    paths=Paths()
    try:
        result=activate(paths=paths)
        print(json.dumps(result,ensure_ascii=False),flush=True)
    except Exception as exc:
        message='O Atelier não pôde ativar a integração: '+str(exc)
        log=paths.data/'activation.log';log.parent.mkdir(parents=True,exist_ok=True)
        with log.open('a') as stream: stream.write(message+'\n')
        print(message,file=sys.stderr)
        try: subprocess.run(['zenity','--error','--title=Atelier','--text='+html.escape(message)],timeout=90,check=False)
        except (OSError,subprocess.SubprocessError): pass
        return 1
    os.execv(str(ROOT/'run-atelier'),[str(ROOT/'run-atelier'),'--enable-desktop'])

if __name__=='__main__': raise SystemExit(main())
