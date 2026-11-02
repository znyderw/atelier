"""Must pass with installed PySide6 before enabling the desktop integration."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QT_QPA_PLATFORMTHEME']=''
os.environ['QT_QUICK_BACKEND']='software'
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
try:
    from PySide6.QtCore import QUrl, QSize, QEventLoop, QTimer
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from atelier.qt import Backend, Images
    AVAILABLE=True
except ImportError:
    AVAILABLE=False

@unittest.skipUnless(AVAILABLE,'PySide6 unavailable: graphical release gate NOT passed')
class Runtime(unittest.TestCase):
    def test_real_python_qml_bridge_and_thumbnail_provider(self):
        from atelier.core import Paths, Store, Desktop
        from atelier.service import Service
        app=QGuiApplication.instance() or QGuiApplication([])
        root=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp:
            paths=Paths(home=Path(temp)/'home',stock=Path(temp)/'stock',data=Path(temp)/'data')
            wallpaper=paths.home/'Wallpapers/test.jpg'; wallpaper.parent.mkdir(parents=True)
            import shutil
            shutil.copy2(root/'ui/assets/cosmic.jpg',wallpaper)
            theme=paths.user/'default/colors.toml';theme.parent.mkdir(parents=True)
            theme.write_text('background="#161e2a"\nforeground="#EEEFEE"\naccent="#757c96"\ngreen="#a7c4da"\n')
            desktop=Desktop(paths,Store(paths),runner=lambda argv,**kw:'[]' if argv[0]=='hyprctl' else '{}')
            service=Service(paths,desktop)
            images=Images(paths); backend=Backend(service,images)
            engine=QQmlApplicationEngine()
            engine.addImageProvider('atelier',images)
            engine.rootContext().setContextProperty('atelierLive',True)
            engine.rootContext().setContextProperty('atelierBackend',backend)
            try:
                engine.load(QUrl.fromLocalFile(str(root/'ui/Main.qml')))
                self.assertTrue(engine.rootObjects())
                # Run Qt's event loop while the Python executor works. QTest.qWait
                # in a Python polling loop can starve that worker of the GIL.
                loop=QEventLoop()
                deadline=QTimer(); deadline.setSingleShot(True)
                deadline.timeout.connect(loop.quit)
                backend.finished.connect(loop.quit)
                backend.dispatch('refresh','{}')
                deadline.start(20000)
                loop.exec()
                deadline.stop()
                backend.finished.disconnect(loop.quit)
                self.assertFalse(backend.busy,'O backend não concluiu a inicialização em 20 segundos.')
                self.assertEqual(len(backend.snapshot['wallpapers']),1)
                self.assertFalse(backend.snapshot['desktopEnabled'])
                token=backend.snapshot['wallpapers'][0]['image'].split('/')[-1]
                image=images.requestImage(token,QSize(),QSize(640,360))
                self.assertFalse(image.isNull())
                self.assertLessEqual(image.width(),640)
                self.assertTrue(list((paths.cache/'thumbnails').glob('*.png')))
            finally:
                for window in engine.rootObjects(): window.close()
                backend.close()
