import QtQuick
import QtTest
import "../../ui" as Atelier
TestCase {
    name:'LivePresentation'
    when:windowShown
    property bool atelierLive:true
    QtObject {
        id:atelierBackend
        property bool busy:false
        property string lastAction:''
        property var lastArgs:({})
        property var snapshot:({wallpapers:[{id:'image:test',name:'Arquivo real',image:'',origin:'Local',kind:'Estático',description:'Arquivo',managed:true}],themes:[],monitors:['DP-1'],monitorIndex:0,applied:{},activeTheme:'default',globalPolicy:'Minha paleta default',exceptions:{},favorites:{},original:{background:'#161e2a',foreground:'#EEEFEE',accent:'#757c96',selection:'#EEEFEE',red:'#988ea5',green:'#a7c4da',yellow:'#cdf5ff',blue:'#757c96',magenta:'#a7a5c6',cyan:'#bfd9fc'},palette:{background:'#161e2a',foreground:'#EEEFEE',accent:'#757c96',selection:'#EEEFEE',red:'#988ea5',green:'#a7c4da',yellow:'#cdf5ff',blue:'#757c96',magenta:'#a7a5c6',cyan:'#bfd9fc'},dirty:false,desktopEnabled:false,diagnostics:'Somente leitura'})
        signal message(string text)
        function dispatch(action,payload) { lastAction=action;lastArgs=JSON.parse(payload) }
    }
    Atelier.Main { id:atelier }
    function test_real_session_wiring() {
        wait(150)
        compare(atelier.live,true)
        compare(atelier.session.wallpapers.length,1)
        compare(atelier.session.wallpapers[0].name,'Arquivo real')
        compare(atelier.selected,null)
        atelier.session.toggleFavorite('image:test')
        compare(atelierBackend.lastAction,'favorite')
        compare(atelierBackend.lastArgs.id,'image:test')
        atelier.session.setMonitor(0)
        compare(atelierBackend.lastArgs.name,'DP-1')
        atelier.session.editColor('accent','#ffffff')
        compare(atelierBackend.lastAction,'editColor')
        compare(atelierBackend.lastArgs.value,'#ffffff')
        compare(atelier.session.desktopEnabled,false)
        atelier.navigate(3); wait(100)
        atelier.session.refresh(); compare(atelierBackend.lastAction,'refresh')
    }
}
