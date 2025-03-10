import serial
from PyQt5.QtWidgets import QComboBox

class customComboBox(QComboBox):
    selected :list = list()
    relays :list = [f"Relay {_}" for _ in range(1,9)]

    def __init__(self, parent=None):
        self.prevText :str|None = None
        super().__init__(parent)
        super().setToolTip("Relay No")

    def dd_changed(self):
        '''Callback when drop down value is changed'''
        if (self.prevText is not None) and (self.prevText in customComboBox.selected):
            customComboBox.selected.remove(self.prevText)

        if self.currentText():
            customComboBox.selected.append(self.currentText())

    def showPopup(self):
        self.prevText = self.currentText() if self.currentText() else None
        self.clear() # Note: this will send the textChanged signal
        self.addItems(
            [x for x in customComboBox.relays if x not in customComboBox.selected]
        )
        super().setToolTip("Relay No")
        super().setCurrentText(self.prevText if self.prevText else '')
        super().showPopup()
