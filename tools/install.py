#!/usr/bin/env python3
"""Review first. --apply only after user approval and graphical validation."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from atelier.core import Paths, atomic_bytes, atomic_json, digest, run
from backup import snapshot
from datetime import datetime, timezone


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--graphical-tests-passed',action='store_true')
    args=parser.parse_args()
    plan=json.loads((ROOT/'packaging/migration-plan.json').read_text())
    plugin=Path(plan['plugin']); launcher=Path(plan['launcher']); candidate=Path(plan['candidate'])
    if digest(plugin)!=plan['before'] or digest(candidate)!=plan['candidateHash']:
        raise RuntimeError('Integração mudou; gere e revise um novo plano.')
    for relative,expected in plan.get('sources',{}).items():
        if digest(ROOT/relative)!=expected: raise RuntimeError('Código mudou desde a preparação: '+relative)
    if launcher.exists() and launcher.read_bytes()!=(ROOT/'packaging/atelier.desktop').read_bytes():
        raise RuntimeError('Launcher Atelier já existe com conteúdo diferente; não será sobrescrito.')
    if not args.apply:
        print(json.dumps(plan,ensure_ascii=False,indent=2)); print('Somente plano. Nenhuma alteração aplicada.'); return
    if not args.graphical_tests_passed: raise RuntimeError('Validação gráfica pendente. Não aplicar.')
    # Require the exact Python used by the launcher to have working bindings.
    run([str(ROOT/'run-atelier'),'--help'])
    interpreter=None
    for command in (str(ROOT/'.venv/bin/python'),sys.executable):
        try:
            run([command,'-c','import PySide6; from PySide6.QtQml import QQmlApplicationEngine'])
            interpreter=command; break
        except Exception: continue
    if interpreter is None: raise RuntimeError('PySide6 não disponível nos Pythons do lançador.')
    code="import sys,unittest; s=unittest.defaultTestLoader.discover(sys.argv[1]); r=unittest.TextTestRunner(verbosity=2).run(s); sys.exit(not r.wasSuccessful() or bool(r.skipped))"
    run([interpreter,'-c',code,str(ROOT/'tests/qt')],timeout=60)
    run(['hyprctl','monitors','-j'])
    home=Path.home(); backup=home/'configs/backups'/('atelier-migration-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    snapshot(home,backup)
    atomic_json(backup/'rollback.json',{'plugin':str(plugin),'before':plan['before'],'after':plan['candidateHash'],
                                      'launcher':str(launcher),'launcherHash':digest(ROOT/'packaging/atelier.desktop')})
    try:
        atomic_bytes(plugin,candidate.read_bytes())
        atomic_bytes(launcher,(ROOT/'packaging/atelier.desktop').read_bytes())
    except Exception:
        # The plugin preimage remains in the validated archive; do not overwrite unrelated changes.
        import tarfile
        with tarfile.open(backup/'backup.tar.gz') as archive:
            atomic_bytes(plugin,archive.extractfile(str(plugin.relative_to(home))).read())
        raise
    print('Migração instalada. Backup:',backup)
    print('Valide a ponte, os dois monitores e o duplo clique antes de encerrar a sessão.')

if __name__=='__main__': main()
