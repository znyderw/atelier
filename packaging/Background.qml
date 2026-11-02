import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import Quickshell.Wayland
import QtQuick
import QtQuick.Effects
import QtQuick.Shapes
import qs.Commons
import qs.Ui

Item {
  id: root

  readonly property string home: Quickshell.env("HOME")
  readonly property string stateHome: home + "/.local/state"
  readonly property string currentBackgroundLink: stateHome + "/omarchy/current/background"

  property string currentBackground: ""
  property string displayedBackground: ""
  property string incomingBackground: ""
  property string oldBackground: ""
  property bool finishingTransition: false
  property int backgroundVersion: 0
  property int revealStartedVersion: -1
  property int pendingThemeVersion: -1
  property string pendingColorsRaw: ""
  property string pendingShellRaw: ""
  property real revealProgress: 1

  // Per-monitor picks from the double-click selector, keyed by screen name.
  // They only apply while the shared background is still the one they were
  // picked over, so a theme switch or `omarchy theme bg next` resets every
  // monitor to the shared background.
  readonly property string monitorBackgroundsPath: stateHome + "/omarchy/background-monitors.json"
  property var monitorBackgrounds: ({})
  property string monitorBackgroundsBase: ""
  property string selectorScreen: ""
  property var engineProjects: ({})
  property string pendingPalette: ""
  property int atelierPaletteExit: 0

  Timer {
    id: paletteQueue
    interval: 250
    repeat: true
    running: root.pendingPalette !== ""
    onTriggered: {
      if (paletteProc.running) return
      paletteProc.command = ["python3", root.engineHelper, "palette", root.pendingPalette]
      root.pendingPalette = ""
      paletteProc.running = true
    }
  }

  Process {
    id: paletteProc
    onExited: function(exitCode, exitStatus) {
      root.atelierPaletteExit = exitCode
      if (exitCode !== 0)
        Quickshell.execDetached(["notify-send", "Cores do wallpaper", "Não foi possível aplicar a paleta. Consulte ~/.local/state/omarchy/wallpaper-engine/palette.log"])
    }
  }
  readonly property string engineHelper: "/home/znyder/Projects/omarchy-wallpaper-manager/packaging/engine_bridge.py"

  function saveMonitorBackgrounds() {
    monitorBackgroundsFile.setText(JSON.stringify({ base: currentBackground, monitors: monitorBackgrounds, engine: engineProjects }, null, 2) + "\n")
  }

  function applyPickerSelection(content) {
    if (!String(content || "").trim()) return
    try {
      var choice = JSON.parse(content)
      var projects = monitorBackgroundsBase === currentBackground ? Object.assign({}, engineProjects) : {}
      if (choice.project) projects[selectorScreen] = choice.project
      else delete projects[selectorScreen]
      engineProjects = projects
      setMonitorBackground(selectorScreen, choice.path)
      pendingPalette = choice.path
    } catch (e) { console.warn("Wallpaper Engine picker:", e) }
  }

  function imageUrl(path) {
    return Util.fileUrl(path)
  }

  function monitorBackground(screenName) {
    if (!currentBackground || monitorBackgroundsBase !== currentBackground) return ""
    return monitorBackgrounds[screenName] || ""
  }

  function setMonitorBackground(screenName, path) {
    path = String(path || "").trim()
    if (!screenName || !path || !currentBackground) return
    var next = monitorBackgroundsBase === currentBackground ? Object.assign({}, monitorBackgrounds) : {}
    next[screenName] = path
    monitorBackgroundsBase = currentBackground
    monitorBackgrounds = next
    saveMonitorBackgrounds()
  }

  function parseMonitorBackgrounds(content) {
    try {
      var parsed = JSON.parse(String(content || ""))
      engineProjects = parsed.engine && typeof parsed.engine === "object" ? parsed.engine : {}
      monitorBackgroundsBase = String(parsed.base || "")
      monitorBackgrounds = parsed.monitors && typeof parsed.monitors === "object" ? parsed.monitors : {}
    } catch (e) {
      engineProjects = {}
      monitorBackgroundsBase = ""
      monitorBackgrounds = {}
    }
    clearStaleMonitorBackgrounds()
  }

  // Forget picks once the shared background moves on, so returning to the
  // same shared background later doesn't bring old picks back.
  function clearStaleMonitorBackgrounds() {
    if (!currentBackground || !monitorBackgroundsBase || monitorBackgroundsBase === currentBackground) return
    engineProjects = {}
    monitorBackgroundsBase = ""
    monitorBackgrounds = {}
    monitorBackgroundsFile.setText("{}\n")
  }

  onCurrentBackgroundChanged: clearStaleMonitorBackgrounds()

  function refreshBackground() {
    if (!readlinkProc.running) readlinkProc.running = true
  }

  function setBackground(path, instant) {
    transitionBackground("", path, path, instant, false)
  }

  function transitionBackground(fromPath, path, finalPath, instant, force) {
    path = String(path || "").trim()
    finalPath = String(finalPath || path).trim()
    fromPath = String(fromPath || "").trim()
    if (!path || (!force && finalPath === currentBackground)) return
    currentBackground = finalPath
    backgroundVersion += 1
    revealStartedVersion = -1

    revealAnimation.stop()
    finishingTransition = false

    if (instant || !displayedBackground) {
      oldBackground = ""
      incomingBackground = ""
      displayedBackground = path
      revealProgress = 1
      return
    }

    oldBackground = fromPath || displayedBackground
    incomingBackground = path
    revealProgress = 0
  }

  function setPendingTheme(colorsB64, shellB64) {
    pendingColorsRaw = Util.decodeBase64(colorsB64)
    pendingShellRaw = Util.decodeBase64(shellB64)
    pendingThemeVersion = backgroundVersion
    pendingThemeFallbackTimer.restart()
  }

  function applyPendingTheme() {
    // Background polling can advance backgroundVersion while a theme switch is
    // pending; the latest theme payload should still apply.
    if (pendingThemeVersion < 0) return
    pendingThemeFallbackTimer.stop()
    Color.loadColors(pendingColorsRaw)
    // Color.loadShell also refreshes Style so the type scale flips with the
    // background reveal instead of waiting for a separate reload path.
    Color.loadShell(pendingShellRaw)
    Style.scheduleRefresh()
    pendingThemeVersion = -1
    pendingColorsRaw = ""
    pendingShellRaw = ""
  }

  function transitionBackgroundWithTheme(fromPath, path, finalPath, colorsB64, shellB64) {
    transitionBackground(fromPath, path, finalPath, false, true)
    setPendingTheme(colorsB64, shellB64)
    if (!incomingBackground || revealProgress >= 1) applyPendingTheme()
  }

  function startReveal(panel) {
    if (!incomingBackground) return
    panel.maskReady = true
    if (revealStartedVersion === backgroundVersion) return
    revealStartedVersion = backgroundVersion
    applyPendingTheme()
    revealAnimation.restart()
  }

  function openSelector(screenName) {
    if (bgSwitchProc.running) return
    selectorScreen = screenName
    bgSwitchProc.command = ["python3", engineHelper, "pick", monitorBackground(screenName) || currentBackground]
    bgSwitchProc.running = true
  }

  function openSelectorForFocused() {
    var monitor = Hyprland.focusedMonitor
    if (monitor && monitor.name) openSelector(monitor.name)
  }

  function openThemeSwitcher() {
    if (!themeSwitchProc.running) themeSwitchProc.running = true
  }

  Process {
    id: bgSwitchProc
    stdout: StdioCollector {
      onStreamFinished: root.applyPickerSelection(text)
    }
  }

  FileView {
    id: monitorBackgroundsFile
    path: root.monitorBackgroundsPath
    printErrors: false
    onLoaded: root.parseMonitorBackgrounds(text())
  }

  Process {
    id: themeSwitchProc
    command: ["bash", "-c", "theme=$(omarchy-theme-switcher); [[ -n $theme ]] && omarchy-theme-set \"$theme\" >/dev/null 2>&1 &"]
    onExited: root.refreshBackground()
  }

  Process {
    id: readlinkProc
    command: ["readlink", "-f", root.currentBackgroundLink]
    stdout: StdioCollector {
      onStreamFinished: root.setBackground(String(text || "").trim(), false)
    }
  }

  IpcHandler {
    target: "background"

    // `omarchy-shell background pickFocused` opens the picker for the
    // focused monitor; `pick <monitor>` for a named one.

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

    function pickFocused(): void {
      root.openSelectorForFocused()
    }

    function pick(screenName: string): void {
      root.openSelector(screenName)
    }

    function refresh(): void {
      root.refreshBackground()
    }

    function set(path: string): void {
      root.setBackground(path, false)
    }

    function setInstant(path: string): void {
      root.setBackground(path, true)
    }

    function transition(fromPath: string, path: string): void {
      root.transitionBackground(fromPath, path, path, false, false)
    }

    function themeTransition(fromPath: string, path: string, finalPath: string, colorsB64: string, shellB64: string): void {
      root.transitionBackgroundWithTheme(fromPath, path, finalPath, colorsB64, shellB64)
    }
  }

  Timer {
    id: pendingThemeFallbackTimer
    interval: 300
    repeat: false
    onTriggered: root.applyPendingTheme()
  }

  NumberAnimation {
    id: revealAnimation
    target: root
    property: "revealProgress"
    from: 0
    to: 1
    duration: 420
    easing.type: Easing.InOutCubic
    onFinished: {
      if (root.incomingBackground) {
        root.displayedBackground = root.currentBackground || root.incomingBackground
        root.finishingTransition = true
      }
      root.revealProgress = 1
    }
  }

  Component.onCompleted: refreshBackground()

  Variants {
    model: Quickshell.screens

    PanelWindow {
      id: panel
      required property var modelData

      screen: modelData
      visible: !remapGuard.remapping
      anchors { top: true; bottom: true; left: true; right: true }

      ScreenMoveRemap {
        id: remapGuard
        window: panel
      }
      color: "transparent"
      // Keep render updates enabled. The background layer has been observed to
      // lose its committed buffer while parked with updatesEnabled=false,
      // leaving a black desktop until omarchy-shell is restarted. The wallpaper
      // itself is static, so this favors correctness over a small render-loop
      // optimization.
      updatesEnabled: true

      property bool maskReady: false

      function maybeStartReveal() {
        if (!root.incomingBackground || root.revealProgress !== 0 || maskReady) return
        if (incomingFrame.status !== Image.Ready) return
        Qt.callLater(function() {
          if (!root.incomingBackground || root.revealProgress !== 0 || maskReady) return
          if (incomingFrame.status !== Image.Ready) return
          root.startReveal(panel)
        })
      }

      WlrLayershell.namespace: "omarchy-background"
      // Keep the transparent click target above the renderer's background surface.
      WlrLayershell.layer: engineProc.running ? WlrLayer.Bottom : WlrLayer.Background
      WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
      exclusionMode: ExclusionMode.Ignore

      // This monitor's own pick, drawn over the shared background. The
      // previous pick stays underneath until the new one has faded in.
      readonly property string ownBackground: root.monitorBackground(modelData.name)
      property string shownOwnBackground: ""
      property string previousOwnBackground: ""

      onOwnBackgroundChanged: {
        if (!ownBackground) return
        previousOwnBackground = ownFrame.opacity > 0 ? shownOwnBackground : ""
        shownOwnBackground = ownBackground
      }


      Item {
        anchors.fill: parent
        visible: !engineProc.running

      Image {
        id: base
        anchors.fill: parent
        source: root.imageUrl(root.displayedBackground)
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: true
        onStatusChanged: {
          if (status === Image.Ready && root.finishingTransition) {
            root.incomingBackground = ""
            root.oldBackground = ""
            root.finishingTransition = false
          }
        }
      }

      Image {
        id: oldFrame
        anchors.fill: parent
        source: root.imageUrl(root.oldBackground)
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: false
        smooth: true
        mipmap: true
        visible: root.oldBackground !== "" && root.revealProgress < 1
        onStatusChanged: panel.maybeStartReveal()
      }

      Item {
        id: incomingLayer
        anchors.fill: parent
        visible: root.incomingBackground !== "" && incomingFrame.status === Image.Ready && (root.revealProgress >= 1 || panel.maskReady)
        layer.enabled: root.incomingBackground !== "" && root.revealProgress < 1
        layer.smooth: true
        layer.effect: MultiEffect {
          maskEnabled: true
          maskSource: revealMask
          maskThresholdMin: 0.5
          maskSpreadAtMin: 0.02
        }

        Image {
          id: incomingFrame
          anchors.fill: parent
          source: root.imageUrl(root.incomingBackground)
          fillMode: Image.PreserveAspectCrop
          asynchronous: true
          cache: false
          smooth: true
          mipmap: true
          onStatusChanged: panel.maybeStartReveal()
        }
      }

      Item {
        id: revealMask
        anchors.fill: parent
        visible: false
        layer.enabled: true

        readonly property real slant: -0.18
        readonly property real centerTop: width / 2 - slant * height / 2
        readonly property real centerBottom: width / 2 + slant * height / 2
        readonly property real reach: width / 2 + Math.abs(slant) * height / 2 + 4
        readonly property real spread: reach * root.revealProgress

        Shape {
          anchors.fill: parent
          antialiasing: true
          preferredRendererType: Shape.CurveRenderer
          ShapePath {
            fillColor: "white"
            strokeColor: "transparent"
            startX: revealMask.centerTop - revealMask.spread; startY: 0
            PathLine { x: revealMask.centerTop + revealMask.spread; y: 0 }
            PathLine { x: revealMask.centerBottom + revealMask.spread; y: revealMask.height }
            PathLine { x: revealMask.centerBottom - revealMask.spread; y: revealMask.height }
            PathLine { x: revealMask.centerTop - revealMask.spread; y: 0 }
          }
        }
      }

      Image {
        anchors.fill: parent
        source: root.imageUrl(panel.previousOwnBackground)
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        visible: panel.previousOwnBackground !== "" && panel.ownBackground !== ""
      }

      Image {
        id: ownFrame
        anchors.fill: parent
        source: root.imageUrl(panel.shownOwnBackground)
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        smooth: true
        mipmap: true
        opacity: panel.ownBackground !== "" && status === Image.Ready ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 300; easing.type: Easing.InOutCubic } }
        onOpacityChanged: if (opacity === 1) panel.previousOwnBackground = ""
      }

      } // Static images are hidden while this monitor has a live wallpaper.

      readonly property string desiredProject: root.monitorBackgroundsBase === root.currentBackground
        ? String(root.engineProjects[modelData.name] || "") : ""
      onDesiredProjectChanged: {
        engineProc.running = false
        engineStart.restart()
      }
      Component.onCompleted: if (desiredProject) engineStart.restart()

      Timer {
        id: engineStart
        interval: 100
        onTriggered: {
          if (engineProc.running) restart()
          else if (panel.desiredProject) engineProc.running = true
        }
      }

      Process {
        id: engineProc
        command: ["python3", root.engineHelper, "render", panel.desiredProject, panel.modelData.name]
        onExited: function(exitCode, exitStatus) {
          if (exitCode !== 0 && panel.desiredProject && !engineStart.running)
            Quickshell.execDetached(["notify-send", "Wallpaper Engine",
              "O wallpaper não pôde ser reproduzido em " + panel.modelData.name + ". Consulte ~/.local/state/omarchy/wallpaper-engine/"])
        }
      }

      Connections {
        target: root
        function onIncomingBackgroundChanged() {
          panel.maskReady = false
          panel.maybeStartReveal()
        }
      }

      MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton
        onDoubleClicked: function(mouse) {
          if (mouse.button === Qt.LeftButton) root.openSelector(panel.modelData.name)
          mouse.accepted = true
        }
      }
    }
  }
}
