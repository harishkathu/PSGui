'''
ps_gui: Control PS2000 and Serial Relay board

Author: Harish Kathalingam (uif51939)
'''
import ctypes
import os
import sys

import serial.tools.list_ports 
from PyQt5.QtWidgets import QMainWindow, QApplication, \
                            QPushButton, QGroupBox, QComboBox, QDoubleSpinBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, Qt
from PyQt5 import uic

from customcombobox import customComboBox 


PS_REGEX = r'^PS 2000'
RELAY_REGEX = r'^(?!PS2000)'

RELAY_BAUD_RATE = 9400

class UI(QMainWindow):
    '''
    UI class to load and use Uic file
    '''
    def __init__(self):
        super().__init__()
        ui = uic.loadUi("Layout.ui", self)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self._set_icon()
        '''Load css'''
        with open(os.path.join(os.getcwd(), "stylesheets/stylesheet.css"), 'r') as s1, \
            open(os.path.join(os.getcwd(), "stylesheets/stylesheet.css"), 'r') as s2:
            self.setStyleSheet(s1.read()+s2.read())

        # Find Items from uic file
        # Title buttons
        self.b_close = ui.Close
        self.b_minimise = ui.Minimise
        self.b_theme = ui.Theme
        ui.TitleFrame.mouseMoveEvent = self.custMouseMoveEvent

        # PoserSupply Items
        self.b_ps = ui.PSButton
        self.dd_pscom = ui.PSCom
        self.sb_onv = ui.OnVoltage
        self.sb_offv = ui.OffVoltage

        # Relay
        self.dd_rcom = ui.RelayCom
        # Battery
        self.b_battery = ui.BatteryButton
        self.dd_battery = ui.BatteryCom

        # Ignition
        self.b_ig = ui.IGButton
        self.dd_ig = ui.IGCom

        # TEST: reload css
        self.reloadcss = ui.ReloadCss
        self.reloadcss.clicked.connect(self._reloadcss)

        self._attach_signals()
        self._set_com_ports()

        self.show()

    def mousePressEvent(self, a0):
        '''
        [Override]
        Get the clicked position of the mouse on the tool.

        Parameters:
            event: represents the mouse press event object.
        '''                                 
        self.clickPosition = a0.globalPos()

    def custMouseMoveEvent(self, a0):
        '''
        [Override]
        This function allows the window to be moved when the left mouse button is pressed and dragged.

        Parameters:
            e: represents the mouse event object.
        '''
        if a0.buttons() == Qt.LeftButton:
            self.move(self.pos() + a0.globalPos() - self.clickPosition)
            self.clickPosition = a0.globalPos()
            a0.accept()

    def _reloadcss(self):
        '''Reload css'''
        s2 = ''
        if self.b_theme.isChecked():
            with open(os.path.join(os.getcwd(), "stylesheets/light.css"), 'r') as f:
                s2 = f.read()
        with open(os.path.join(os.getcwd(), "stylesheets/stylesheet.css"), 'r') as f:
            self.setStyleSheet(f.read() + s2)
            print("Reload CSS")
        
    def _set_icon(self):
        '''Set application Icon'''
        app_icon = QIcon()
        cur_path = os.getcwd()
        app_icon.addFile(os.path.join(cur_path, "icons/electric.png"), QSize(24,24))
        app.setWindowIcon(app_icon)

        # To show icon in taskbar
        MYAPPID = u'Harish.PSGui.1.0' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(MYAPPID)

    def _set_com_ports(self):
        '''Set the COM ports drop downs'''
        # Set PS COM dro-down
        com_list = serial.tools.list_ports.grep(PS_REGEX)
        com_list = [desc for _, desc, _ in sorted(com_list)]
        self.dd_pscom.setToolTip("Select PS2000 COM port")
        self.dd_pscom.addItems(com_list)
        for i, com in enumerate(com_list):
            self.dd_rcom.setItemData(i, com, Qt.ToolTipRole)

        # Set Relay COM drop-down
        com_list = serial.tools.list_ports.grep(RELAY_REGEX)
        com_list = [desc for _, desc, _ in sorted(com_list)]
        self.dd_pscom.setToolTip("Select Relay COM port")
        self.dd_rcom.addItems(com_list)
        for i, com in enumerate(com_list):
            self.dd_rcom.setItemData(i, com, Qt.ToolTipRole)

    def _attach_signals(self):
        '''Configure all buttons''' 
        self.b_ps.clicked.connect(self.ps_toggled)
        self.b_battery.clicked.connect(self.battery_toggled)
        self.b_ig.clicked.connect(self.ig_toggled)
        self.b_close.clicked.connect(self.close)
        self.b_minimise.clicked.connect(self.showMinimized)
        self.b_theme.clicked.connect(self.theme_clicked)
        self.dd_battery.currentIndexChanged.connect(self.dd_battery.dd_changed)
        self.dd_ig.currentIndexChanged.connect(self.dd_ig.dd_changed)
        self.dd_pscom.currentIndexChanged.connect(self.dd_pscom_changed)
        self.dd_rcom.currentIndexChanged.connect(self.dd_rcom_changed)

    def dd_pscom_changed(self):
        '''Set tool tip for DropDown once value selected'''
        self.dd_pscom.setToolTip(self.dd_pscom.currentText())
    
    def dd_rcom_changed(self):
        '''Set tool tip for DropDown once value selected'''
        self.dd_rcom.setToolTip(self.dd_rcom.currentText())

    def ps_toggled(self):
        '''PSButton click event'''
        print(f"PS checked: {self.b_ps.isChecked()}")

    def battery_toggled(self):
        '''BatteryButton click event'''
        relay = self.dd_battery.currentText()
        cmd = f'RL{relay[-1]}{int(self.b_battery.isChecked())}' if relay else ''
        print(f"B+: {cmd}")

    def ig_toggled(self):
        '''IGButton click event'''
        relay = self.dd_ig.currentText()
        cmd = f'RL{relay[-1]}{int(self.b_ig.isChecked())}' if relay else ''
        print(f"IG: {cmd}")

    def theme_clicked(self):
        '''Theme click event'''
        s2 = ''
        if self.b_theme.isChecked():
            with open(os.path.join(os.getcwd(), "stylesheets/light.css"), 'r') as f:
                s2 = f.read()
        with open(os.path.join(os.getcwd(), "stylesheets/stylesheet.css"), 'r') as s1:
            self.setStyleSheet(s1.read() + s2)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    Window = UI()
    app.exec_()
