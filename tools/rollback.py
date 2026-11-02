#!/usr/bin/env python3
"""Restore only integration files if they still match the installed candidate."""
import argparse
import json
from pathlib import Path
import sys
import tarfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from atelier.core import digest, atomic_bytes

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('backup',type=Path); parser.add_argument('--apply',action='store_true'); parser.add_argument('--keep-launcher',action='store_true'); args=parser.parse_args()
    plan=json.loads((args.backup/'rollback.json').read_text())
    plugin=Path(plan['plugin']); launcher=Path(plan['launcher'])
    if digest(plugin)!=plan['after']: raise RuntimeError('Plugin mudou após a instalação; restauração automática cancelada.')
    if launcher.exists() and digest(launcher)!=plan['launcherHash']: raise RuntimeError('Launcher mudou; restauração automática cancelada.')
    with tarfile.open(args.backup/'backup.tar.gz') as archive:
        original=archive.extractfile(str(plugin.relative_to(Path.home()))).read()
    if __import__('hashlib').sha256(original).hexdigest()!=plan['before']: raise RuntimeError('Backup divergente.')
    if not args.apply: print('Restauraria',plugin,'e removeria apenas o launcher Atelier. Use --apply após revisão.'); return
    atomic_bytes(plugin,original)
    if not args.keep_launcher: launcher.unlink(missing_ok=True)
    print('Integração anterior restaurada. Dados e temas do Atelier foram preservados.')

if __name__=='__main__': main()
