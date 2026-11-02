import QtQuick
QtObject {
    // Presentation fixtures only. No files, processes, IPC, or system integrations.
    property int revision: 0
    property var monitors: ['DP-1 · Principal', 'HDMI-A-1 · Secundário']
    property int monitorIndex: 0
    property var applied: ({'0': 'cosmic', '1': 'waves'})
    property string activeTheme: 'default'
    property string globalPolicy: 'Minha paleta default'
    property var exceptions: ({'forest': 'Cores do wallpaper'})
    property var favorites: ({'cosmic': true, 'forest': true})
    property var wallpapers: [
        {id:'cosmic', name:'Entre estrelas', origin:'Local', kind:'Estático', image:'cosmic.jpg', description:'Uma janela para o céu. Imagem ilustrativa do catálogo de demonstração.'},
        {id:'forest', name:'Floresta suspensa', origin:'Workshop', kind:'Cena', image:'forest.jpg', description:'Cena simulada do Steam Workshop. A miniatura é estática; nenhum renderizador é iniciado.'},
        {id:'waves', name:'Maré azul', origin:'Local', kind:'Estático', image:'waves.jpg', description:'Formas suaves em azul. Arquivo ilustrativo, sem vínculo com o wallpaper aplicado.'},
        {id:'meadow', name:'Depois da chuva', origin:'Workshop', kind:'Vídeo', image:'meadow.jpg', description:'Vídeo simulado. A interface utiliza apenas uma imagem reduzida.'},
        {id:'totoro', name:'Pequeno refúgio', origin:'Local', kind:'Estático', image:'totoro.jpg', description:'Uma pausa na rotina. Imagem de exemplo.'},
        {id:'dunes', name:'Horizonte quente', origin:'Local', kind:'Estático', image:'dunes.jpg', description:'Tons de areia e luz. Imagem de exemplo.'}
    ]
    property var themes: [
        {id:'default', name:'default', origin:'Personalizado', image:'cosmic.jpg', colors:['#161e2a','#757c96','#EEEFEE','#a7c4da'], protected:true},
        {id:'catppuccin', name:'Catppuccin', origin:'Sistema', image:'waves.jpg', colors:['#1e1e2e','#cba6f7','#cdd6f4','#a6e3a1'], protected:true},
        {id:'everforest', name:'Everforest', origin:'Sistema', image:'forest.jpg', colors:['#2d353b','#a7c080','#d3c6aa','#7fbbb3'], protected:true},
        {id:'aurora', name:'Aurora', origin:'Criado no app', image:'meadow.jpg', colors:['#191c2b','#b7a6ed','#e9e7f5','#86c8ba'], protected:false}
    ]
    property var original: ({background:'#161e2a',foreground:'#EEEFEE',accent:'#757c96',selection:'#EEEFEE',red:'#988ea5',green:'#a7c4da',yellow:'#cdf5ff',blue:'#757c96',magenta:'#a7a5c6',cyan:'#bfd9fc'})
    property var palette: Object.assign({}, original)
    property bool dirty: false
    readonly property bool busy: false
    readonly property bool desktopEnabled: false
    function setMonitor(index) { monitorIndex=index }
    function setGlobal(value) { globalPolicy=value }
    function setTheme(id) { activeTheme=id }
    function applyPalette() {}
    function renameTheme(item,name) { themes=themes.map(t=>t.id===item.id?Object.assign({},t,{name:name}):t) }
    function importImage(url) {}
    function removeWallpaper(id) {}
    function loadTheme(item) {
        let next=Object.assign({}, original);
        next.background=item.colors[0]; next.accent=item.colors[1];
        next.foreground=item.colors[2]; next.green=item.colors[3];
        original=next; palette=Object.assign({}, next); dirty=false;
    }
    function toggleFavorite(id) { let v=Object.assign({},favorites); v[id]=!v[id]; favorites=v; revision++ }
    function applyWallpaper(id) { let v=Object.assign({},applied); v[String(monitorIndex)]=id; applied=v; revision++ }
    function restore(id) { globalPolicy='Minha paleta default'; let v=Object.assign({},exceptions); delete v[id]; exceptions=v; activeTheme='default'; revision++ }
    function setException(id,value) { let v=Object.assign({},exceptions); if(value==='Seguir padrão') delete v[id]; else v[id]=value; exceptions=v; revision++ }
    function editColor(key,value) { if(!/^#[0-9a-fA-F]{6}$/.test(value)) return false; let v=Object.assign({},palette); v[key]=value; palette=v; dirty=true; return true }
    function revert() { palette=Object.assign({},original); dirty=false }
    function extract() { palette={background:'#18212a',foreground:'#e5edf0',accent:'#81b8b4',selection:'#b3d5cf',red:'#cb9ca6',green:'#a0c8b3',yellow:'#e2d5ac',blue:'#91b7d4',magenta:'#bcaccf',cyan:'#8bcbd0'}; dirty=true }
    function duplicateTheme(item,name) { let v=themes.slice(); let id='demo-'+Date.now(); v.push({id:id,name:name,origin:'Criado no app',image:item.image,colors:item.colors,protected:false}); themes=v; return id }
    function removeTheme(id) { themes=themes.filter(t=>t.id!==id || t.protected || activeTheme===id) }
    function saveTheme(name) { duplicateTheme({image:'cosmic.jpg',colors:[palette.background,palette.accent,palette.foreground,palette.green]},name); original=Object.assign({},palette); dirty=false }
}
