import QtQuick
import QtQuick.Controls
TextField {
    id: control
    implicitHeight: 40; leftPadding: 14; rightPadding: 14
    color: '#EAEAEA'; placeholderTextColor: '#B0B0B0'; font.pixelSize: 13
    selectByMouse: true
    background: Rectangle { radius: 9; color: '#121212'; border.color: control.activeFocus ? '#4D7DF3' : '#303030' }
}
