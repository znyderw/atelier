import QtQuick
import QtQuick.Controls
Button {
    id: control
    property bool primary: false
    property bool danger: false
    implicitHeight: 38
    hoverEnabled: true
    leftPadding: 16; rightPadding: 16
    font.pixelSize: 13
    contentItem: Text { text: control.text; font: control.font; color: !control.enabled ? '#636a79' : control.primary ? '#FFFFFF' : control.danger ? '#f3a3ac' : '#EAEAEA'; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
    background: Rectangle { radius: 9; color: control.primary ? (control.hovered ? '#5382EC' : '#4D7DF3') : (control.hovered ? '#262626' : '#1B1B1B'); border.color: control.primary ? 'transparent' : '#303030'; opacity: control.enabled ? 1 : 0.5; Behavior on color { ColorAnimation { duration: 120 } } }
    ToolTip.visible: hovered && ToolTip.text.length > 0
}
