import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "components"

ApplicationWindow {
    id: win
    width: 1380; height: 900; minimumWidth: 900; minimumHeight: 650
    visible: true; title: live ? 'Atelier · Wallpapers e temas' : 'Atelier · Wallpapers e temas — demonstração'
    color: '#0E0E0E'
    palette.window: '#121212'; palette.windowText: '#EAEAEA'; palette.text: '#EAEAEA'
    palette.base: '#121212'; palette.button: '#1F1F1F'; palette.buttonText: '#EAEAEA'
    palette.highlight: '#4D7DF3'; palette.highlightedText: '#121212'
    font.family: bodyFamily; font.pixelSize: 14
    readonly property bool live: typeof atelierLive!=='undefined' && atelierLive
    readonly property var session: live && liveLoader.item ? liveLoader.item : demo
    Loader { id:liveLoader; active:win.live; sourceComponent:Component { LiveSession {} } }
    Connections { target:win.live ? atelierBackend : null; ignoreUnknownSignals:true
        function onMessage(message) { win.tell(message) }
    }
    property int page: 0
    property string search: ''
    property string originFilter: 'Todas as origens'
    property string kindFilter: 'Todos os tipos'
    property bool onlyFavorites: false
    property int wallLimit:48
    onVisibleWallsChanged: wallLimit=48
    property var selected: null
    property var displayedWallpaper: live ? ({id:'',name:'',image:'',origin:'',kind:'',description:''}) : demo.wallpapers[0]
    onSelectedChanged: { if (selected) displayedWallpaper=selected }
    readonly property var installedFonts: Qt.fontFamilies()
    readonly property string bodyFamily: installedFonts.indexOf('Inter')>=0 ? 'Inter' : installedFonts.indexOf('Satoshi')>=0 ? 'Satoshi' : installedFonts.indexOf('Geist Sans')>=0 ? 'Geist Sans' : 'Liberation Sans'
    readonly property string identityFamily: installedFonts.indexOf('Euclid Flex')>=0 ? 'Euclid Flex' : installedFonts.indexOf('URW Gothic')>=0 ? 'URW Gothic' : bodyFamily
    property string selectedTheme: 'default'
    property string editKey: 'accent'
    property string toastText: ''
    property string confirmAction: ''
    property var contextItem: ({})
    property string renameAction: ''
    property bool compare: false
    property var shownPalette: Object.assign({background:'#121212',foreground:'#EAEAEA',accent:'#4D7DF3',green:'#B0B0B0',red:'#B0B0B0',yellow:'#B0B0B0',blue:'#4D7DF3',magenta:'#D4DCFA',cyan:'#D4DCFA'},compare ? session.original : session.palette)
    property var visibleWalls: {
        let rev=session.revision;
        return session.wallpapers.filter(w=> (!search || w.name.toLowerCase().includes(search.toLowerCase())) && (originFilter==='Todas as origens'||w.origin===originFilter) && (kindFilter==='Todos os tipos'||w.kind===kindFilter) && (!onlyFavorites||session.favorites[w.id]))
    }
    property var visibleThemes: session.themes.filter(t=>(!search||t.name.toLowerCase().includes(search.toLowerCase())) && (originFilter==='Todas as origens'||originFilter===t.origin))
    DemoSession { id: demo }
    function asset(name) { return !name ? '' : /^(file:|https?:|qrc:|image:)/.test(name) ? name : Qt.resolvedUrl('assets/'+name) }
    function tell(message) { toastText=message; toastTimer.restart() }
    function confirm(action,title,text) { confirmAction=action; confirmation.title=title; confirmation.message=text; confirmation.open() }
    function navigate(index) { page=index; search=''; originFilter='Todas as origens'; kindFilter='Todos os tipos' }

    // A quiet grid behind the content; repaints only on resize.
    Canvas {
        anchors.fill: parent; opacity:0.55
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            let ctx=getContext('2d'); ctx.reset();
            ctx.strokeStyle='#1F1F1F'; ctx.lineWidth=1;
            ctx.beginPath();
            for(let x=0.5;x<width;x+=32) { ctx.moveTo(x,0); ctx.lineTo(x,height) }
            for(let y=0.5;y<height;y+=32) { ctx.moveTo(0,y); ctx.lineTo(width,y) }
            ctx.stroke();
        }
    }
    RowLayout {
        anchors.fill: parent; spacing: 0
        Rectangle {
            Layout.preferredWidth: win.width<1100 ? 166 : 188; Layout.fillHeight: true; color:'#121212'
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 20; spacing: 9
                Text { text:'<font color="#4D7DF3">Ate</font><font color="#5382EC">lier</font>'; textFormat:Text.RichText; font.family:win.identityFamily; font.pixelSize:24; font.letterSpacing:1; font.weight:Font.Bold; Layout.topMargin:6; Layout.bottomMargin:24 }
                Repeater {
                    model: ['Wallpapers','Temas','Editor','Configurações']
                    delegate: Rectangle {
                        required property int index; required property string modelData
                        Layout.fillWidth:true; Layout.preferredHeight:44; radius:9; color:win.page===index?'#1A284D':navMouse.containsMouse?'#1F1F1F':'transparent'
                        Text { anchors.verticalCenter:parent.verticalCenter; anchors.left:parent.left; anchors.leftMargin:12; text:modelData; color:win.page===index?'#E2E8FD':'#B0B0B0'; font.pixelSize:13 }
                        MouseArea { id:navMouse; anchors.fill:parent; hoverEnabled:true; cursorShape:Qt.PointingHandCursor; onClicked:win.navigate(index) }
                    }
                }
                Item { Layout.fillHeight:true }
                Text { text:win.live ? (win.session.busy ? '● Carregando…' : win.session.desktopEnabled ? '● Atelier' : '● Avaliação local') : '● Demonstração'; color:'#939dc4'; font.pixelSize:11
                    ToolTip.visible: demoHover.hovered
                    ToolTip.text:win.live ? 'Biblioteca real. Aplicação no desktop exige a ponte e aprovação.' : 'Dados simulados. As alterações duram apenas nesta janela.'
                    HoverHandler { id:demoHover }
                }
            }
        }
        ColumnLayout {
            Layout.fillWidth:true; Layout.fillHeight:true; spacing:0
            ColumnLayout {
                Layout.fillWidth:true; Layout.fillHeight:true; Layout.margins:20; spacing:16
                RowLayout {
                    visible:win.page<2; Layout.fillWidth:true; spacing:10
                    Field { Layout.fillWidth:true; placeholderText:win.page===0?'Pesquisar wallpapers…':'Pesquisar temas…'; text:win.search; onTextEdited:win.search=text }
                    Choice { currentIndex:Math.max(0,model.indexOf(win.originFilter)); Layout.preferredWidth:win.width<1100?132:170; model:win.page===0?['Todas as origens','Local','Workshop']:['Todas as origens','Sistema','Personalizado','Criado no app']; onActivated:win.originFilter=currentText }
                    Choice { visible:win.page===0; currentIndex:Math.max(0,model.indexOf(win.kindFilter)); Layout.preferredWidth:win.width<1100?120:150; model:['Todos os tipos','Estático','Cena','Vídeo']; onActivated:win.kindFilter=currentText }
                    Action { visible:win.page===0; text:win.width<1100?(win.onlyFavorites?'★':'☆'):(win.onlyFavorites?'★ Favoritos':'☆ Favoritos'); ToolTip.text:'Mostrar favoritos'; onClicked:win.onlyFavorites=!win.onlyFavorites }
                    Action { visible:win.live; text:'↻'; ToolTip.text:'Atualizar biblioteca e monitores'; enabled:!win.session.busy; onClicked:win.session.refresh() }
                    Action { visible:win.page===0; text:'＋ Importar'; onClicked:importDialog.open() }
                    Action { visible:win.page===1; text:'＋ Novo tema'; primary:true; onClicked:{ win.navigate(2); if(!win.live)win.tell('Edite a paleta e salve sua criação de demonstração.') } }
                }
                StackLayout {
                    currentIndex:win.page; Layout.fillWidth:true; Layout.fillHeight:true
                    // WALLPAPERS
                    RowLayout {
                        id:wallpaperLayout; objectName:'wallpaperLayout'
                        spacing:0
                        ColumnLayout {
                            Layout.fillWidth:true; Layout.fillHeight:true; spacing:12
                            ScrollView {
                                id:wallGallery; objectName:'wallGallery'
                                contentHeight:wallGrid.implicitHeight
                                ScrollBar.horizontal.policy:ScrollBar.AlwaysOff
                                Layout.fillWidth:true; Layout.fillHeight:true; clip:true
                                contentWidth:availableWidth
                                GridLayout {
                                    id:wallGrid; objectName:'wallGrid'
                                    width:wallGallery.availableWidth; columns:Math.max(1,Math.floor((width+14)/294)); uniformCellWidths:true; columnSpacing:14; rowSpacing:14
                                    Repeater { model:win.visibleWalls.slice(0,win.wallLimit)
                                        delegate: Rectangle {
                                            id:wallCard; objectName:'wallCard-'+modelData.id
                                            required property var modelData
                                            Layout.fillWidth:true; Layout.minimumWidth:0; Layout.preferredWidth:280; Layout.preferredHeight:(width-14)*9/16+65
                                            radius:12; color:'#161616'; border.color:win.selected && win.selected.id===modelData.id?'#4D7DF3':'#262626'; border.width:win.selected && win.selected.id===modelData.id?2:1
                                            ColumnLayout { anchors.fill:parent; anchors.margins:7; spacing:8
                                                Item { Layout.fillWidth:true; Layout.fillHeight:true; clip:true
                                                    Image { anchors.fill:parent; source:win.asset(wallCard.modelData.image); sourceSize.width:620; sourceSize.height:340; asynchronous:true; fillMode:Image.PreserveAspectFit }
                                                    Rectangle { anchors.left:parent.left; anchors.top:parent.top; anchors.margins:8; radius:5; color:'#d9171d28'; width:typeText.width+16; height:24
                                                        Text { id:typeText; anchors.centerIn:parent; text:wallCard.modelData.kind==='Estático'?'Imagem': '▶ '+wallCard.modelData.kind; color:'#eff1f8'; font.pixelSize:10 }
                                                    }
                                                    Action { anchors.right:parent.right; anchors.top:parent.top; anchors.margins:7; width:34; height:30; leftPadding:0; rightPadding:0; text:session.favorites[wallCard.modelData.id]?'★':'☆'; onClicked:session.toggleFavorite(wallCard.modelData.id); ToolTip.text:'Favoritar' }
                                                }
                                                RowLayout { Layout.fillWidth:true; Layout.leftMargin:5; Layout.rightMargin:5
                                                    ColumnLayout { Layout.fillWidth:true; spacing:3
                                                        Text { Layout.fillWidth:true; elide:Text.ElideRight; text:wallCard.modelData.name; color:'#EAEAEA'; font.pixelSize:13 }
                                                        Text { text:wallCard.modelData.origin; color:'#B0B0B0'; font.pixelSize:11 }
                                                    }
                                                    Text { text:session.applied[String(session.monitorIndex)]===wallCard.modelData.id?'●':''; color:'#adcfb6'; font.pixelSize:17 }
                                                    Action { text:'•••'; Layout.preferredWidth:32; leftPadding:0; rightPadding:0; onClicked:{win.contextItem=wallCard.modelData; wallMenu.popup()} }
                                                }
                                            }
                                            TapHandler { acceptedButtons:Qt.LeftButton; gesturePolicy:TapHandler.ReleaseWithinBounds; onTapped:win.selected=wallCard.modelData }
                                            TapHandler { acceptedButtons:Qt.RightButton; onTapped:{win.contextItem=wallCard.modelData;wallMenu.popup()} }
                                        }
                                    }
                                    Action { Layout.columnSpan:wallGrid.columns; Layout.alignment:Qt.AlignHCenter; visible:win.visibleWalls.length>win.wallLimit; text:'Carregar mais'; onClicked:win.wallLimit+=48 }
                                }
                                Label { visible:win.visibleWalls.length===0; anchors.centerIn:parent; text:'Nenhum wallpaper encontrado.\nTente outro nome ou remova os filtros.'; color:'#a5b0c2'; horizontalAlignment:Text.AlignHCenter }
                            }
                        }
                        Item {
                            id:contextPanel; objectName:'contextPanel'
                            property real reveal:win.selected ? 1 : 0
                            readonly property real panelWidth:win.width<1150?260:290
                            Layout.preferredWidth:(panelWidth+16)*reveal
                            Layout.minimumWidth:0; Layout.maximumWidth:Layout.preferredWidth
                            Layout.fillHeight:true; visible:reveal>0; enabled:win.selected!==null; clip:true
                            Behavior on reveal { NumberAnimation { duration:170; easing.type:Easing.OutCubic } }
                            Rectangle {
                                anchors.right:parent.right; width:contextPanel.panelWidth; height:parent.height
                                opacity:contextPanel.reveal; color:'#161616'; radius:14; border.color:'#262626'
                            ScrollView { anchors.fill:parent; anchors.margins:16; contentWidth:availableWidth; clip:true
                                ColumnLayout { width:parent.width; spacing:14
                                    RowLayout { Layout.fillWidth:true
                                        Item { Layout.fillWidth:true }
                                        Action { objectName:'closePanel'; text:'×'; implicitWidth:30; implicitHeight:30; leftPadding:0; rightPadding:0; ToolTip.text:'Fechar seleção'; Accessible.name:'Fechar seleção'; onClicked:win.selected=null }
                                    }
                                    Image { Layout.fillWidth:true; Layout.preferredHeight:180; source:win.asset(win.displayedWallpaper.image); sourceSize.width:600; sourceSize.height:360; asynchronous:true; fillMode:Image.PreserveAspectFit; clip:true }
                                    Text { text:win.displayedWallpaper.name; color:'#EAEAEA'; font.pixelSize:16; Layout.fillWidth:true; wrapMode:Text.Wrap }
                                    Action { text:'Detalhes'; onClicked:detailsDialog.open() }
                                    Rectangle { Layout.fillWidth:true; Layout.preferredHeight:1; color:'#262626' }
                                    Text { text:'Monitor'; color:'#B0B0B0'; font.pixelSize:10; font.letterSpacing:1 }
                                    Choice { Layout.fillWidth:true; model:session.monitors; currentIndex:session.monitorIndex; onActivated:session.setMonitor(currentIndex) }
                                    Text { text:session.applied[String(session.monitorIndex)]===win.displayedWallpaper.id?'● Aplicado neste monitor':'Disponível para este monitor'; color:'#a9c2b1'; font.pixelSize:11 }
                                    Action { Layout.fillWidth:true; text:'Aplicar wallpaper'; primary:true; enabled:!win.live || (win.session.desktopEnabled && !win.session.busy && win.session.monitors.length>0 && win.session.monitorIndex>=0); onClicked:{session.applyWallpaper(win.displayedWallpaper.id);if(!win.live)win.tell('Wallpaper alterado somente na demonstração.')} }
                                    Text { text:'Cores'; color:'#B0B0B0'; font.pixelSize:10; Layout.topMargin:10; font.letterSpacing:1 }
                                    Choice { id:exceptionChoice; Layout.fillWidth:true; model:['Seguir padrão','Minha paleta default','Cores do wallpaper','Manter cores atuais'].concat(win.live ? session.themes.filter(t=>t.id!=='default').map(t=>'Paleta: '+t.id) : []); currentIndex:Math.max(0,model.indexOf(session.exceptions[win.displayedWallpaper.id]||'Seguir padrão')); enabled:!win.live || win.session.desktopEnabled; onActivated:{session.setException(win.displayedWallpaper.id,currentText);if(!win.live)win.tell('Preferência simulada atualizada.')} }
                                    Text { Layout.fillWidth:true; text:'Padrão global: '+session.globalPolicy+'\nAs cores são compartilhadas entre monitores.'; color:'#B0B0B0'; font.pixelSize:11; wrapMode:Text.Wrap; lineHeight:1.4 }
                                    Action { Layout.fillWidth:true; text:'Restaurar minha paleta default'; enabled:!win.live || win.session.desktopEnabled; onClicked:win.confirm('restore',win.live ? 'Restaurar default' : 'Restaurar default · demo','Voltar à paleta default e remover apenas a exceção deste wallpaper? As demais preferências serão mantidas.') }
                                }
                            }
                        }
                    }
                    }
                    // THEMES
                    ScrollView {
                        id:themeGallery; objectName:'themeGallery'
                        contentHeight:themeGrid.implicitHeight
                        ScrollBar.horizontal.policy:ScrollBar.AlwaysOff
                        clip:true; contentWidth:availableWidth
                        GridLayout { id:themeGrid; width:themeGallery.availableWidth; columns:Math.max(1,Math.floor((width+18)/298)); uniformCellWidths:true; columnSpacing:18; rowSpacing:18
                            Repeater { model:win.visibleThemes
                                delegate:Rectangle {
                                    id:themeCard; required property var modelData
                                    Layout.fillWidth:true; Layout.minimumWidth:0; Layout.preferredWidth:280; Layout.preferredHeight:340; radius:12; color:'#161616'; border.color:session.activeTheme===modelData.id?'#4D7DF3':'#262626'
                                    ColumnLayout { anchors.fill:parent; anchors.margins:12; spacing:12
                                        Item { Layout.fillWidth:true; Layout.preferredHeight:182; clip:true
                                            Image { anchors.fill:parent; source:win.asset(themeCard.modelData.image); sourceSize.width:600; asynchronous:true; fillMode:Image.PreserveAspectCrop }
                                            Rectangle { anchors.fill:parent; color:'#350a1020' }
                                            Rectangle { anchors.centerIn:parent; width:parent.width*0.7; height:85; color:themeCard.modelData.colors[0]; radius:7
                                                Column { anchors.fill:parent; anchors.margins:12; spacing:7
                                                    Text { text:'●  ●  ●'; color:themeCard.modelData.colors[1]; font.pixelSize:9 }
                                                    Text { text:'❯  hello, omarchy'; color:themeCard.modelData.colors[2]; font.family:'monospace'; font.pixelSize:10 }
                                                    Rectangle { width:parent.width*0.7; height:5; radius:2; color:themeCard.modelData.colors[3] }
                                                }
                                            }
                                        }
                                        RowLayout { Layout.fillWidth:true
                                            ColumnLayout { Layout.fillWidth:true; spacing:4
                                                Text { text:themeCard.modelData.name; color:'#EAEAEA'; font.pixelSize:17 }
                                                Text { text:themeCard.modelData.origin+(themeCard.modelData.id==='default'?' · protegido':''); color:'#B0B0B0'; font.pixelSize:11 }
                                            }
                                            Text { text:session.activeTheme===themeCard.modelData.id?'● Ativo':''; color:'#b8c5e3'; font.pixelSize:10 }
                                        }
                                        Row { spacing:7; Repeater { model:themeCard.modelData.colors; delegate:Rectangle { required property string modelData; width:23; height:15; radius:4; color:modelData } } }
                                        RowLayout { Layout.fillWidth:true
                                            Action { text:'Aplicar'; primary:true; Layout.fillWidth:true; enabled:!win.live || win.session.desktopEnabled; onClicked:{win.contextItem=themeCard.modelData;win.confirm('theme',win.live ? 'Aplicar cores do tema' : 'Aplicar tema · demo',win.live ? 'Aplicar as cores de '+themeCard.modelData.name+' preservando os wallpapers?' : 'Simular a aplicação de '+themeCard.modelData.name+'?')} }
                                            Action { text:'Editar'; onClicked:{session.loadTheme(themeCard.modelData);win.selectedTheme=themeCard.modelData.name;win.compare=false;win.navigate(2)} }
                                            Action { text:'•••'; onClicked:{win.contextItem=themeCard.modelData;themeMenu.popup()} }
                                        }
                                    }
                                }
                            }
                        }
                        Label { visible:win.visibleThemes.length===0; anchors.centerIn:parent; text:'Nenhum tema encontrado.'; color:'#a6b1c4' }
                    }
                    // DESIGNER
                    ColumnLayout {
                        spacing:16
                        RowLayout { Layout.fillWidth:true
                            Text { text:win.selectedTheme+' / rascunho'; color:'#cbd2e4'; font.pixelSize:16 }
                            Text { text:session.dirty?'● Alterações locais':'● Sem alterações'; color:'#9caacf'; font.pixelSize:11 }
                            Item { Layout.fillWidth:true }
                            Action { text:'Reverter'; enabled:session.dirty; onClicked:session.revert() }
                            Action { text:'Salvar como…'; onClicked:{win.renameAction='save';nameField.text='Minha aurora';nameDialog.open()} }
                            Action { text:'Aplicar'; primary:true; enabled:!win.live || win.session.desktopEnabled; onClicked:win.confirm('palette',win.live ? 'Aplicar paleta' : 'Aplicar paleta · demo',win.live ? 'Aplicar a paleta salva como tema, preservando os wallpapers?' : 'Confirmar a aplicação simulada desta paleta?') }
                        }
                        RowLayout {
                            Layout.fillWidth:true; Layout.fillHeight:true; spacing:22
                            Rectangle { Layout.preferredWidth:win.width<1150?300:360; Layout.fillHeight:true; radius:12; color:'#161616'; border.color:'#262626'
                                ColumnLayout { anchors.fill:parent; anchors.margins:18; spacing:14
                                    RowLayout { Layout.fillWidth:true
                                        Text { text:'Paleta de cores'; color:'#e2e7f3'; font.pixelSize:17 }
                                        Item { Layout.fillWidth:true }
                                        Text { text:'HEX'; color:'#7e8da5'; font.pixelSize:10 }
                                    }
                                    Action { Layout.fillWidth:true; text:'Extrair do wallpaper'; enabled:!win.live || !!win.displayedWallpaper.id; onClicked:{session.extract(win.displayedWallpaper.id);if(!win.live)win.tell('Paleta ilustrativa carregada.')} }
                                    ScrollView { Layout.fillWidth:true; Layout.fillHeight:true; contentWidth:availableWidth; clip:true
                                        ColumnLayout { width:parent.width; spacing:9
                                            Repeater { model:Object.keys(session.palette)
                                                delegate:RowLayout {
                                                    required property string modelData
                                                    Layout.fillWidth:true
                                                    Rectangle { Layout.preferredWidth:29; Layout.preferredHeight:29; radius:7; color:session.palette[modelData]; border.color:'#667085'
                                                        TapHandler { onTapped:{win.editKey=modelData;colorPicker.selectedColor=session.palette[modelData];colorPicker.open()} }
                                                    }
                                                    Text { Layout.fillWidth:true; text:modelData; color:'#CCCCCC'; font.pixelSize:12 }
                                                    Field { Layout.preferredWidth:96; implicitHeight:34; text:session.palette[modelData]; font.family:'monospace'; font.pixelSize:11; maximumLength:7; onEditingFinished:{if(!session.editColor(modelData,text)){text=session.palette[modelData];win.tell('Use uma cor hexadecimal de seis dígitos, como #757c96.')}} }
                                                }
                                            }
                                        }
                                    }
                                    Text { Layout.fillWidth:true; text:win.live ? 'Salve como um novo tema. O original será preservado.' : 'Paleta ilustrativa.'; color:'#8594ab'; font.pixelSize:11; wrapMode:Text.Wrap }
                                }
                            }
                            ColumnLayout { Layout.fillWidth:true; Layout.fillHeight:true; spacing:14
                                RowLayout { Layout.fillWidth:true
                                    Text { text:'PRÉVIA DO DESKTOP'; color:'#8c9ab0'; font.pixelSize:11; font.letterSpacing:1 }
                                    Item { Layout.fillWidth:true }
                                    Action { text:win.compare?'Ver editada':'Comparar original'; onClicked:win.compare=!win.compare }
                                }
                                Rectangle { Layout.fillWidth:true; Layout.fillHeight:true; radius:13; color:win.shownPalette.background; clip:true; border.color:'#3b455a'
                                    Image { anchors.fill:parent; source:win.live ? win.asset(win.displayedWallpaper.image) : win.asset('cosmic.jpg'); fillMode:Image.PreserveAspectCrop; opacity:0.34; sourceSize.width:900; asynchronous:true }
                                    Rectangle { anchors.top:parent.top; width:parent.width; height:35; color:win.shownPalette.background
                                        Text { anchors.left:parent.left; anchors.leftMargin:15; anchors.verticalCenter:parent.verticalCenter; text:'◈    1   2   3'; color:win.shownPalette.accent; font.pixelSize:11 }
                                        Text { anchors.right:parent.right; anchors.rightMargin:15; anchors.verticalCenter:parent.verticalCenter; text:'♫     ◉     14:32'; color:win.shownPalette.foreground; font.pixelSize:11 }
                                    }
                                    Rectangle { anchors.left:parent.left; anchors.top:parent.top; anchors.margins:24; anchors.topMargin:62; width:parent.width-48; height:parent.height*0.44; color:win.shownPalette.background; border.color:win.shownPalette.accent; radius:9
                                        Column { anchors.fill:parent; anchors.margins:18; spacing:12
                                            Text { text:'●  ●  ●     terminal'; color:win.shownPalette.accent; font.pixelSize:11 }
                                            Text { text:'❯  fastfetch'; color:win.shownPalette.green; font.family:'monospace'; font.pixelSize:12 }
                                            Text { text:'omarchy  /  seu espaço, suas cores'; color:win.shownPalette.foreground; font.family:'monospace'; font.pixelSize:win.width<1100?10:12 }
                                            Row { spacing:0; Repeater { model:['red','green','yellow','blue','magenta','cyan']; delegate:Rectangle { required property string modelData; width:25; height:18; color:win.shownPalette[modelData] } } }
                                        }
                                    }
                                    Rectangle { anchors.right:parent.right; anchors.bottom:parent.bottom; anchors.margins:24; width:Math.min(parent.width-48,270); height:126; radius:10; color:win.shownPalette.background; border.color:win.shownPalette.accent
                                        Column { anchors.fill:parent; anchors.margins:14; spacing:12
                                            Text { text:'Aplicativos'; color:win.shownPalette.foreground; font.pixelSize:13 }
                                            Rectangle { width:parent.width; height:28; radius:5; color:win.shownPalette.accent; Text { anchors.centerIn:parent; text:'▧  Wallpapers e temas'; color:win.shownPalette.background; font.pixelSize:11 } }
                                            Text { text:'▣  Arquivos       ⌘  Terminal'; color:win.shownPalette.foreground; font.pixelSize:11 }
                                        }
                                    }
                                }
                                Text { text:(win.compare?'Original':'Editada')+' · Prévia local'; color:'#8a99b0'; font.pixelSize:11 }
                            }
                        }
                    }
                    // SETTINGS
                    ScrollView { clip:true; contentWidth:availableWidth
                        ColumnLayout { width:parent.width; spacing:18
                            Repeater { model:[
                                {title:'Comportamento das cores',body:'As cores são globais. As exceções por wallpaper têm prioridade sobre a preferência geral.'},
                                {title:'Monitores',body:win.live ? (win.session.monitors.join('\n') || 'Sessão Hyprland indisponível. Atualize a biblioteca após conectar a sessão.') : 'DP-1 · Principal\nHDMI-A-1 · Secundário\nDados ilustrativos.'},
                                {title:'Wallpaper Engine',body:win.live ? 'O plugin existente continua responsável pelos renderizadores. O Atelier não inicia processos paralelos.' : 'Demonstração: nenhum renderizador é iniciado.'},
                                {title:'Biblioteca e miniaturas',body:win.live ? win.session.wallpapers.length+' wallpapers. Importe imagens para gerenciá-las pelo Atelier.' : '6 imagens de exemplo.'},
                                {title:'Backup e recuperação',body:'Backup real validado antes do desenvolvimento. A interface antiga e o plugin atual continuam preservados.'},
                                {title:'Diagnóstico de compatibilidade',body:win.live ? (win.session.diagnosticText || 'Carregando…') : 'Atelier · Demonstração. Adaptadores desconectados.'}
                            ]; delegate:Rectangle {
                                required property var modelData; Layout.fillWidth:true; implicitHeight:settingsColumn.implicitHeight+36; color:'#161616'; radius:12; border.color:'#262626'
                                ColumnLayout { id:settingsColumn; anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top; anchors.margins:18; spacing:10
                                    Text { text:modelData.title; color:'#EAEAEA'; font.pixelSize:17 }
                                    Text { text:modelData.body; color:'#B0B0B0'; font.pixelSize:12; Layout.fillWidth:true; wrapMode:Text.Wrap; lineHeight:1.5 }
                                    Choice { visible:modelData.title==='Comportamento das cores'; Layout.preferredWidth:260; model:['Minha paleta default','Cores do wallpaper','Manter cores atuais'].concat(win.live ? session.themes.filter(t=>t.id!=='default').map(t=>'Paleta: '+t.id) : []); enabled:!win.live || win.session.desktopEnabled; currentIndex:Math.max(0,model.indexOf(session.globalPolicy)); onActivated:session.setGlobal(currentText) }
                                    Action { visible:modelData.title==='Diagnóstico de compatibilidade'; text:win.live ? 'Atualizar diagnóstico' : 'Ver estado da demonstração'; onClicked:{if(win.live)win.session.refresh();else win.tell('Modo isolado: nenhuma integração real está conectada.')}  }
                                }
                            } }
                        }
                    }
                }
            }
        }
    }
    Dialog { id:detailsDialog; title:win.displayedWallpaper.name; anchors.centerIn:parent; width:Math.min(420,win.width-60); modal:true; standardButtons:Dialog.Close
        contentItem:Label { text:win.displayedWallpaper.origin+' · '+win.displayedWallpaper.kind+'\n\n'+win.displayedWallpaper.description; wrapMode:Text.Wrap; color:'#b4bfd3'; padding:12 }
    }
    Menu { id:wallMenu
        MenuItem { text:'Ver detalhes'; onTriggered:win.selected=win.contextItem }
        MenuItem { text:'Favoritar / desfavoritar'; onTriggered:session.toggleFavorite(win.contextItem.id) }
        MenuItem { text:win.contextItem.origin==='Workshop'?'Gerenciar na Steam…':'Remover wallpaper…'; enabled:win.contextItem.origin==='Workshop' || !!win.contextItem.managed; onTriggered:{ if(win.contextItem.origin==='Workshop') Qt.openUrlExternally('steam://url/CommunityFilePage/'+win.contextItem.id.replace('workshop:','')); else win.confirm('deleteWallpaper','Remover wallpaper','Mover esta imagem importada para a lixeira recuperável do Atelier?') } }
    }
    Menu { id:themeMenu
        MenuItem { text:'Duplicar…'; onTriggered:{win.renameAction='duplicate';nameField.text=win.contextItem.name+' — cópia';nameDialog.open()} }
        MenuItem { text:'Renomear…'; enabled:!win.contextItem.protected; onTriggered:{win.renameAction='rename';nameField.text=win.contextItem.name;nameDialog.open()} }
        MenuItem { text:'Excluir…'; enabled:!win.contextItem.protected && session.activeTheme!==win.contextItem.id; onTriggered:win.confirm('deleteTheme',win.live ? 'Remover tema' : 'Excluir tema · demo',win.live ? 'Mover este rascunho para a lixeira recuperável do Atelier?' : 'Remover este tema somente do catálogo simulado?') }
        MenuItem { text:'Restaurar de backup…'; enabled:false }
    }
    Dialog { id:confirmation; property string message:''; anchors.centerIn:parent; width:Math.min(480,win.width-60); modal:true; standardButtons:Dialog.Ok|Dialog.Cancel
        contentItem:Label { text:confirmation.message; wrapMode:Text.Wrap; color:'#dbe2ef'; padding:10 }
        onAccepted:{
            if(win.confirmAction==='restore') session.restore(win.displayedWallpaper.id)
            else if(win.confirmAction==='theme') session.setTheme(win.contextItem.id)
            else if(win.confirmAction==='deleteTheme') session.removeTheme(win.contextItem.id)
            else if(win.confirmAction==='palette') session.applyPalette()
            else if(win.confirmAction==='deleteWallpaper') session.removeWallpaper(win.contextItem.id)
            if(!win.live)win.tell('Ação confirmada na demonstração. Seu sistema não foi alterado.')
        }
    }
    Dialog { id:nameDialog; title:win.live ? 'Nome do tema' : 'Nome do tema · demonstração'; anchors.centerIn:parent; width:400; modal:true; standardButtons:Dialog.Save|Dialog.Cancel
        contentItem:Field { id:nameField; placeholderText:'Nome do novo tema'; maximumLength:60 }
        onAccepted:{
            let name=nameField.text.trim(); if(!name){win.tell('Informe um nome.');return}
            if(session.themes.some(t=>t.name.toLowerCase()===name.toLowerCase() && (win.renameAction!=='rename'||t.id!==win.contextItem.id))){win.tell('Esse nome já existe. Escolha outro nome.');return}
            if(win.renameAction==='save') session.saveTheme(name)
            else if(win.renameAction==='duplicate') session.duplicateTheme(win.contextItem,name)
            else session.renameTheme(win.contextItem,name)
            if(!win.live)win.tell('Tema salvo somente na sessão de demonstração.')
        }
    }
    ColorDialog { id:colorPicker; title:'Cor · '+win.editKey; onAccepted:session.editColor(win.editKey,selectedColor.toString()) }
    FileDialog { id:importDialog; title:win.live ? 'Importar imagem' : 'Selecionar imagem para a demonstração'; nameFilters:['Imagens (*.png *.jpg *.jpeg *.webp)']; onAccepted:session.importImage(selectedFile) }
    Rectangle { anchors.horizontalCenter:parent.horizontalCenter; anchors.bottom:parent.bottom; anchors.bottomMargin:28; width:Math.min(win.width-80,toastLabel.implicitWidth+40); height:toastLabel.implicitHeight+26; color:'#343e55'; border.color:'#58627d'; radius:10; visible:toastTimer.running; z:10
        Text { id:toastLabel; anchors.centerIn:parent; width:Math.min(win.width-120,implicitWidth); text:win.toastText; color:'#edf0fb'; font.pixelSize:13; wrapMode:Text.Wrap; horizontalAlignment:Text.AlignHCenter }
    }
    Timer { id:toastTimer; interval:4500 }
    Shortcut { sequence:'Escape'; enabled:win.page===0 && win.selected!==null; onActivated:win.selected=null }
    Shortcut { sequence:'Ctrl+1'; onActivated:win.navigate(0) }
    Shortcut { sequence:'Ctrl+2'; onActivated:win.navigate(1) }
    Shortcut { sequence:'Ctrl+3'; onActivated:win.navigate(2) }
    Shortcut { sequence:'Ctrl+4'; onActivated:win.navigate(3) }
    // Opt-in capture and exit for local validation, never enabled during normal use.
    Timer { interval:1500; running:Qt.application.arguments.indexOf('--capture')!==-1; onTriggered:{
        let args=Qt.application.arguments; let n=args.indexOf('--page'); if(n>=0) win.navigate(Number(args[n+1]));captureDelay.start()
    } }
    Timer { id:captureDelay; interval:1000; onTriggered:win.contentItem.grabToImage(function(result){result.saveToFile(Qt.application.arguments[Qt.application.arguments.indexOf('--capture')+1]);Qt.quit()}) }
}
