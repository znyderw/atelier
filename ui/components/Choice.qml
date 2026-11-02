import QtQuick
import QtQuick.Controls
ComboBox {
    id: control
    implicitWidth: 170; implicitHeight: 40
    font.pixelSize: 13
    contentItem: Text { text: control.displayText; color: '#EAEAEA'; font: control.font; verticalAlignment: Text.AlignVCenter; leftPadding: 12; rightPadding: 26; elide: Text.ElideRight }
    background: Rectangle { color: '#1B1B1B'; radius: 9; border.color: '#303030' }
    delegate: ItemDelegate { width: control.width; text: modelData; highlighted: control.highlightedIndex === index }
}
