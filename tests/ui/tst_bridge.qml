import QtQuick
import QtTest
TestCase {
    name:'DesktopBridgeContract'
    QtObject { id:quickshellMock; property var screens:[{name:'DP-1'}] }
    QtObject { id:bgSwitchProc; property bool running:false }
    QtObject { id:paletteProc; property bool running:false }
    QtObject { id:root; property int atelierPaletteExit:0; property string pendingPalette:''; property string selectorScreen:''; property string lastChoice:''
        function applyPickerSelection(choice) { lastChoice=choice }
    }
    QtObject { id:bridge


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
        for (var i=0; i<quickshellMock.screens.length; ++i)
          if (quickshellMock.screens[i].name === screenName) found = true
        if (!found) return JSON.stringify({ok:false,error:"Monitor desconectado"})
        if (bgSwitchProc.running || paletteProc.running || root.pendingPalette)
          return JSON.stringify({ok:false,error:"Background ocupado; aguarde a operação atual"})
        root.atelierPaletteExit = 0
        root.selectorScreen = screenName
        root.applyPickerSelection(JSON.stringify(choice))
        return JSON.stringify({ok:true,version:1,monitor:screenName})
      } catch (error) { return JSON.stringify({ok:false,error:String(error)}) }
    }

    }
    function test_valid_and_invalid_requests() {
        compare(JSON.parse(bridge.atelierCapabilities()).version,1)
        let payload=JSON.stringify({version:1,path:'/tmp/test.png',project:''})
        compare(JSON.parse(bridge.atelierApply('DP-1',payload)).ok,true)
        compare(root.selectorScreen,'DP-1')
        compare(JSON.parse(root.lastChoice).path,'/tmp/test.png')
        let before=root.lastChoice
        compare(JSON.parse(bridge.atelierApply('missing',payload)).ok,false)
        compare(JSON.parse(bridge.atelierApply('DP-1','broken')).ok,false)
        compare(JSON.parse(bridge.atelierApply('DP-1',JSON.stringify({version:2,path:'/tmp/test.png',project:''}))).ok,false)
        compare(JSON.parse(bridge.atelierApply('DP-1',JSON.stringify({version:1,path:'relative',project:''}))).ok,false)
        paletteProc.running=true
        compare(JSON.parse(bridge.atelierApply('DP-1',payload)).ok,false)
        compare(root.lastChoice,before)
        paletteProc.running=false;root.pendingPalette='/tmp/queued.png'
        compare(JSON.parse(bridge.atelierApply('DP-1',payload)).ok,false)
    }
}
