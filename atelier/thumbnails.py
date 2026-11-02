"""Persistent, bounded thumbnails. No desktop interaction."""
import hashlib
from pathlib import Path
import subprocess
from .core import AtelierError, atomic_bytes, lock

class ThumbnailCache:
    def __init__(self,directory): self.directory=Path(directory)
    def get(self,source):
        source=Path(source).resolve(); info=source.stat()
        token=hashlib.sha256(f'{source}:{info.st_size}:{info.st_mtime_ns}:640x360-v1'.encode()).hexdigest()
        target=self.directory/(token+'.png')
        if target.is_file(): return target
        with lock(self.directory/(token+'.lock')):
            if target.is_file(): return target
            try:
                result=subprocess.run(['ffmpeg','-v','error','-i',str(source),'-frames:v','1',
                    '-vf','scale=640:360:force_original_aspect_ratio=decrease','-f','image2pipe','-vcodec','png','-'],
                    capture_output=True,check=True,timeout=15)
            except (OSError,subprocess.SubprocessError) as exc: raise AtelierError('Miniatura indisponível: '+str(exc)) from exc
            if not result.stdout.startswith(b'\x89PNG\r\n\x1a\n'): raise AtelierError('Miniatura inválida.')
            atomic_bytes(target,result.stdout)
        self.prune()
        return target
    def prune(self,limit=256*1024*1024):
        entries=sorted(self.directory.glob('*.png'),key=lambda p:p.stat().st_mtime)
        size=sum(p.stat().st_size for p in entries)
        for path in entries:
            if size<=limit: break
            size-=path.stat().st_size; path.unlink(missing_ok=True)
