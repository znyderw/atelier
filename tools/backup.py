#!/usr/bin/env python3
"""Read-only snapshot of the existing integration, with archive verification."""
import hashlib
import json
from pathlib import Path
import tarfile
from datetime import datetime, timezone

RELEVANT = ['.local/share/omarchy-wallpaper-engine', '.config/omarchy/themes',
            '.config/omarchy/shell.json', '.config/omarchy/wallpaper-control.json',
            '.config/omarchy/plugins/io.github.jholloway12.per-monitor-background',
            '.local/state/omarchy/background-monitors.json', '.local/state/omarchy/current',
            '.local/share/applications/omarchy-wallpaper-control.desktop']

def snapshot(home, destination, paths=RELEVANT):
    home, destination = Path(home), Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {'files': {}, 'symlinks': {}}
    with tarfile.open(destination/'backup.tar.gz', 'w:gz', dereference=False) as archive:
        for relative in paths:
            source = home/relative
            if not source.exists() and not source.is_symlink():
                continue
            archive.add(source, arcname=relative)
            for item in ([source] + sorted(source.rglob('*')) if source.is_dir() and not source.is_symlink() else [source]):
                key = str(item.relative_to(home))
                if item.is_symlink():
                    manifest['symlinks'][key] = str(item.readlink())
                elif item.is_file():
                    with item.open('rb') as stream:
                        manifest['files'][key] = hashlib.file_digest(stream, 'sha256').hexdigest()
    (destination/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    with tarfile.open(destination/'backup.tar.gz') as archive:
        for key, digest in manifest['files'].items():
            with archive.extractfile(key) as stream:
                assert hashlib.file_digest(stream,'sha256').hexdigest()==digest, key
        for key, target in manifest['symlinks'].items():
            assert archive.getmember(key).linkname == target, key
    (destination/'VALIDATED.txt').write_text(f"{len(manifest['files'])} files; {len(manifest['symlinks'])} links; all verified\n")
    return destination

if __name__=='__main__':
    home=Path.home()
    print(snapshot(home,home/'configs/backups'/('atelier-functional-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))))
