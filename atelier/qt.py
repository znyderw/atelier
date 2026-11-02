"""Async Qt bridge. A single worker serializes state changes and desktop requests."""
from concurrent.futures import ThreadPoolExecutor
import json
import traceback
from pathlib import Path
from PySide6.QtCore import QObject, Property, Signal, Slot
from .service import Service

class Backend(QObject):
    changed=Signal()
    finished=Signal(object, str)
    message=Signal(str)
    def __init__(self,service=None,images=None):
        super().__init__()
        self.images=images
        self.service=service or Service(); self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='atelier')
        self._busy=False; self._pending=0; self._snapshot={'wallpapers':[],'themes':[],'monitors':[],'monitorIndex':-1,
            'applied':{},'favorites':{},'exceptions':{},'activeTheme':'','globalPolicy':'',
            'palette':{},'original':{},'dirty':False,'diagnostics':'Carregando…','desktopEnabled':self.service.desktop.enabled}
        self.finished.connect(self._finish)

    @Property('QVariantMap',notify=changed)
    def snapshot(self): return self._snapshot
    @Property(bool,notify=changed)
    def busy(self): return self._busy

    @Slot(str,str)
    def dispatch(self,action,payload='{}'):
        if self._pending>=16:
            self.message.emit('Aguarde as operações pendentes terminarem.'); return
        self._pending+=1; self._busy=True; self.changed.emit()
        def work():
            try:
                result=self.service.dispatch(action,json.loads(payload)); self.finished.emit(result,'')
            except Exception as exc:
                # Preserve UI state on failure; log only to Atelier's own data directory.
                try:
                    log=self.service.p.data/'atelier.log'; log.parent.mkdir(parents=True,exist_ok=True)
                    with log.open('a') as stream: traceback.print_exc(file=stream)
                except OSError: pass
                self.finished.emit(None,str(exc))
        self.pool.submit(work)

    @Slot(object,str)
    def _finish(self,result,error):
        if result is not None:
            if self.images:
                for item in result['wallpapers']+result['themes']:
                    image=item.get('image','')
                    if image.startswith('file:'):
                        try: item['image']=self.images.register(unquote(urlparse(image).path))
                        except OSError: item['image']=''
            self._snapshot=result
        self._pending-=1; self._busy=self._pending>0; self.changed.emit()
        self.message.emit(error or 'Operação concluída.')

    def close(self): self.pool.shutdown(wait=True,cancel_futures=True)

# The QML images request thumbnails lazily on Qt's image loading thread.
# Sources are registered by the backend, never interpreted as arbitrary paths.
import hashlib
import threading
from urllib.parse import urlparse, unquote
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider
from .thumbnails import ThumbnailCache

class Images(QQuickImageProvider):
    def __init__(self,paths):
        super().__init__(QQuickImageProvider.Image)
        self.registry={}; self.guard=threading.Lock(); self.cache=ThumbnailCache(paths.cache/'thumbnails')
    def register(self,path):
        path=Path(path).resolve(); info=path.stat(); token=hashlib.sha256(f'{path}:{info.st_size}:{info.st_mtime_ns}'.encode()).hexdigest()
        with self.guard: self.registry[token]=path
        return 'image://atelier/'+token
    def requestImage(self,id,size,requestedSize):
        with self.guard: path=self.registry.get(id)
        image=QImage()
        if path is not None:
            try: image=QImage(str(self.cache.get(path)))
            except Exception: pass
        size.setWidth(image.width()); size.setHeight(image.height())
        return image
