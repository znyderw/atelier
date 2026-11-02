import QtQuick
QtObject {
    readonly property var state: atelierBackend.snapshot
    readonly property bool busy: atelierBackend.busy
    readonly property bool desktopEnabled: !!state.desktopEnabled
    readonly property var wallpapers: state.wallpapers || []
    readonly property var themes: state.themes || []
    readonly property var monitors: state.monitors || []
    readonly property int monitorIndex: state.monitorIndex || 0
    readonly property var applied: state.applied || ({})
    readonly property string activeTheme: state.activeTheme || ''
    readonly property string globalPolicy: state.globalPolicy || ''
    readonly property var exceptions: state.exceptions || ({})
    readonly property var favorites: state.favorites || ({})
    readonly property var original: state.original || ({})
    readonly property var palette: state.palette || ({})
    readonly property bool dirty: !!state.dirty
    readonly property int revision: 0
    readonly property string diagnosticText: state.diagnostics || ''
    function call(action,args) { atelierBackend.dispatch(action,JSON.stringify(args || {})) }
    function toggleFavorite(id) { call('favorite',{id:id}) }
    function setMonitor(index) { if(monitors[index]) call('monitor',{name:monitors[index]}) }
    function applyWallpaper(id) { call('wallpaper',{id:id,monitor:monitors[monitorIndex] || ''}) }
    function restore(id) { call('restore',{id:id}) }
    function setException(id,value) { call('exception',{id:id,value:value}) }
    function setGlobal(value) { call('global',{value:value,monitor:monitors[monitorIndex] || ''}) }
    function setTheme(id) { call('theme',{id:id}) }
    function applyPalette() { call('palette') }
    function editColor(key,value) { if(!/^#[0-9a-fA-F]{6}$/.test(value)) return false; call('editColor',{key:key,value:value}); return true }
    function revert() { call('revert') }
    function extract(id) { call('extract',{id:id}) }
    function loadTheme(item) { call('loadTheme',{id:item.id}) }
    function duplicateTheme(item,name) { call('duplicateTheme',{id:item.id,name:name}) }
    function renameTheme(item,name) { call('renameTheme',{id:item.id,name:name}) }
    function removeTheme(id) { call('removeTheme',{id:id}) }
    function saveTheme(name) { call('saveTheme',{name:name}) }
    function importImage(url) { call('import',{path:decodeURIComponent(String(url).replace(/^file:\/\//,''))}) }
    function removeWallpaper(id) { call('remove',{id:id}) }
    function refresh() { call('refresh') }
}
