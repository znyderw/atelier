#!/usr/bin/env python3
"""Build reviewable integration artifacts. Never touches the installed plugin."""
import difflib
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from atelier.core import Paths, atomic_json, digest

BRIDGE='''
    // Atelier bridge v1. The existing background plugin remains the sole player owner.
    function atelierCapabilities(): string {
      return JSON.stringify({ version: 1, apply: true, busy: paletteProc.running || root.pendingPalette !== "", paletteExit: root.atelierPaletteExit })
    }

    function atelierApply(screenName: string, payload: string): string {
      try {
        var choice = JSON.parse(payload)
        if (choice.version !== 1 || typeof choice.path !== "string" || choice.path.charAt(0) !== "/" ||
            typeof choice.project !== "string" || (choice.project && choice.project.charAt(0) !== "/"))
          return JSON.stringify({ok:false,error:"Escolha inválida"})
        var found = false
        for (var i=0; i<Quickshell.screens.length; ++i)
          if (Quickshell.screens[i].name === screenName) found = true
        if (!found) return JSON.stringify({ok:false,error:"Monitor desconectado"})
        if (bgSwitchProc.running || paletteProc.running || root.pendingPalette)
          return JSON.stringify({ok:false,error:"Background ocupado; aguarde a operação atual"})
        root.atelierPaletteExit = 0
        root.selectorScreen = screenName
        root.applyPickerSelection(JSON.stringify(choice))
        return JSON.stringify({ok:true,version:1,monitor:screenName})
      } catch (error) { return JSON.stringify({ok:false,error:String(error)}) }
    }
'''

def prepare(source,app=ROOT):
    text=source
    marker='    function pickFocused(): void {'
    if marker not in text or 'function atelierCapabilities' in text:
        raise RuntimeError('Contrato do plugin mudou; revisão manual necessária.')
    text=text.replace(marker,BRIDGE+'\n'+marker,1)
    text=text.replace('  property string pendingPalette: ""','  property string pendingPalette: ""\n  property int atelierPaletteExit: 0',1)
    text=text.replace('      if (exitCode !== 0)\n        Quickshell.execDetached', '      root.atelierPaletteExit = exitCode\n      if (exitCode !== 0)\n        Quickshell.execDetached',1)
    old='home + "/.local/share/omarchy-wallpaper-engine/picker.py"'
    if old not in text: raise RuntimeError('Helper não reconhecido.')
    text=text.replace(old,json.dumps(str(app/'packaging/engine_bridge.py')))
    old='''    bgSwitchProc.command = ["python3", engineHelper, "pick", monitorBackground(screenName) || currentBackground]
    bgSwitchProc.running = true'''
    if old not in text: raise RuntimeError('Seletor não reconhecido.')
    # Keep the native picker on desktop double-click; Atelier is launcher-only.
    old='''        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(mouse) {
          if (mouse.button === Qt.RightButton)
            Quickshell.execDetached(["python3", root.home + "/.local/share/omarchy-wallpaper-engine/control.py", "--screen", panel.modelData.name])
        }'''
    if old not in text: raise RuntimeError('Integração de clique não reconhecida.')
    text=text.replace(old,'        acceptedButtons: Qt.LeftButton')
    return text

if __name__=='__main__':
    p=Paths(); source=p.plugin.read_text(); candidate=prepare(source)
    dest=ROOT/'packaging/Background.qml'; dest.write_text(candidate)
    (ROOT/'packaging/background.patch').write_text(''.join(difflib.unified_diff(source.splitlines(True),candidate.splitlines(True),fromfile=str(p.plugin),tofile='Background.qml (Atelier candidate)')))
    launcher='''[Desktop Entry]
Type=Application
Name=Atelier
Comment=Wallpapers e temas
Exec="'''+str(ROOT/'activate-and-run')+'''"
Icon=preferences-desktop-wallpaper
Terminal=false
Categories=Settings;DesktopSettings;
'''
    (ROOT/'packaging/atelier.desktop').write_text(launcher)
    atomic_json(ROOT/'packaging/migration-plan.json',{'schema':1,'plugin':str(p.plugin),'before':digest(p.plugin),'candidate':str(dest),'candidateHash':digest(dest),'launcher':str(p.home/'.local/share/applications/atelier.desktop'),'legacyPreserved':True,'sources':{str(item.relative_to(ROOT)):digest(item) for pattern in ('atelier/*.py','ui/*.qml','ui/components/*.qml','packaging/engine_bridge.py','main.py','run-atelier','activate-and-run','tools/*.py','tests/qt/*.py') for item in ROOT.glob(pattern) if item.is_file()}})
    print('Candidatos preparados em',ROOT/'packaging','— integração instalada intacta.')
