#!/usr/bin/env python3
"""Atelier. Default is real-library evaluation, with desktop writes disabled."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--enable-desktop',action='store_true',help='Only after approving and installing the versioned bridge')
    parser.add_argument('--monitor',default='')
    args,qtargs=parser.parse_known_args()
    if args.demo and args.enable_desktop: parser.error('Demo não aceita operações reais.')
    os.environ.setdefault('QT_QUICK_CONTROLS_STYLE','Basic')
    try:
        import PySide6
        from PySide6.QtCore import QUrl, qVersion
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
    except ImportError:
        print('PySide6 indisponível. Consulte README.md. Nenhuma integração foi alterada.',file=sys.stderr); return 2
    app=QGuiApplication([sys.argv[0]]+qtargs)
    app.setApplicationName('Atelier'); app.setApplicationVersion('0.3.0')
    app.setOrganizationName('Atelier')
    from atelier.core import Paths, Store, Desktop
    paths=Paths(); handle=None; backend=None; server=None
    socket_name=str(Path(os.environ.get('XDG_RUNTIME_DIR','/tmp'))/f'atelier-{os.getuid()}.sock')
    if not args.demo:
        runtime=Path(os.environ.get('XDG_RUNTIME_DIR','/tmp'))
        handle=(runtime/f'atelier-{os.getuid()}.lock').open('a')
        try: fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            from PySide6.QtNetwork import QLocalSocket
            client=QLocalSocket(); client.connectToServer(socket_name)
            if not client.waitForConnected(1000):
                print('Outra instância está inicializando. Tente novamente.',file=sys.stderr); return 1
            client.write((json.dumps({'monitor':args.monitor})+'\n').encode()); client.waitForBytesWritten(1000)
            client.disconnectFromServer(); return 0
    engine=QQmlApplicationEngine()
    engine.rootContext().setContextProperty('atelierLive',not args.demo)
    if not args.demo:
        from atelier.qt import Backend, Images
        from atelier.service import Service
        service=Service(paths,Desktop(paths,Store(paths),enabled=args.enable_desktop))
        images=Images(paths)
        engine.addImageProvider('atelier',images)
        backend=Backend(service,images)
        engine.rootContext().setContextProperty('atelierBackend',backend)
    print(f'Python {sys.version.split()[0]} | PySide6 {PySide6.__version__} | Qt {qVersion()} | {app.platformName()}',flush=True)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent/'ui/Main.qml')))
    if not engine.rootObjects(): return 1
    if backend:
        if args.monitor: service.store.update(lambda d:d.update(selectedMonitor=args.monitor))
        backend.dispatch('refresh','{}')
        app.aboutToQuit.connect(backend.close)
        from PySide6.QtNetwork import QLocalServer
        server=QLocalServer(); QLocalServer.removeServer(socket_name)
        if not server.listen(socket_name):
            print('Não foi possível criar o canal da instância única.',file=sys.stderr); backend.close(); return 1
        clients=[]
        def incoming():
            client=server.nextPendingConnection(); clients.append(client)
            def ready():
                if not client.canReadLine(): return
                try:
                    payload=json.loads(bytes(client.readLine()).decode())
                    monitor=payload.get('monitor','')
                    if monitor: backend.dispatch('monitor',json.dumps({'name':monitor}))
                except (ValueError,TypeError): pass
                window=engine.rootObjects()[0]
                window.show(); window.raise_(); window.requestActivate()
                client.disconnectFromServer()
            client.readyRead.connect(ready)
            def gone():
                if client in clients: clients.remove(client)
                client.deleteLater()
            client.disconnected.connect(gone)
            ready()
        server.newConnection.connect(incoming)
        app.aboutToQuit.connect(server.close)
    return app.exec()

if __name__=='__main__': raise SystemExit(main())
