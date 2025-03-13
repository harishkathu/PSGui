'''
ps_gui: Control PS2000 and Serial Relay board

Author: Harish Kathalingam (uif51939)
'''
import ctypes
import os
import sys
import traceback

import serial.tools.list_ports 
from PyQt5.QtWidgets import QMainWindow, QApplication, \
                            QPushButton, QGroupBox, QComboBox, \
                            QDoubleSpinBox, QErrorMessage, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5 import uic

from customcombobox import customComboBox 
from ps2000 import PS2000

RELAY_BAUD_RATE = 9600
PS_REGEX = r"^PS 2000"
RELAY_REGEX = fr"^(?!({PS_REGEX}))"
PS_COM_LIST = sorted(tuple(serial.tools.list_ports.grep(RELAY_REGEX)))
RELAY_COM_LIST = sorted(tuple(serial.tools.list_ports.grep(RELAY_REGEX)))

class UI(QMainWindow):
    '''
    UI class to load and use Uic file
    '''
    def __init__(self):
        self.PSDev = None
        self.RelayDev = None
        self.timer = QTimer()
        self.timer.setInterval(3000)
        self.timer.setSingleShot(True)

        super().__init__()
        self.ui = uic.loadUi("Layout.ui", self)
        self._set_window_property()
        '''Load css'''
        with open(os.path.join(os.getcwd(), "stylesheets/stylesheet.css"), 'r') as s1, \
            open(os.path.join(os.getcwd(), "stylesheets/stylesheet.css"), 'r') as s2:
            self.setStyleSheet(s1.read()+s2.read())

        # Find Items from uic file
        # Title buttons
        self.b_close = self.ui.Close
        self.b_minimise = self.ui.Minimise
        self.b_theme = self.ui.Theme
        self.ui.TitleFrame.mouseMoveEvent = self.custMouseMoveEvent

        # PoserSupply Items
        self.b_ps = self.ui.PSButton
        self.dd_pscom = self.ui.PSCom
        self.sb_onv = self.ui.OnVoltage
        self.sb_offv = self.ui.OffVoltage

        # Relay
        self.dd_rcom = self.ui.RelayCom
        # Battery
        self.b_battery = self.ui.BatteryButton
        self.dd_battery = self.ui.BatteryCom

        # Ignition
        self.b_ig = self.ui.IGButton
        self.dd_ig = self.ui.IGCom

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


    @staticmethod
    def _gen_payload(cmd:str):
        cmd = cmd + '\n\r'
        return cmd.encode()


    def _timer_to(self):
        self.ui.Message.clear()


    def _set_window_property(self):
        '''Set application Icon'''
        # we make sure the window is opened at the topmost
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        app_icon = QIcon()
        cur_path = os.getcwd()
        app_icon.addFile(os.path.join(cur_path, "icons/electric.png"), QSize(24,24))
        app.setWindowIcon(app_icon)

        # To show icon in taskbar
        MYAPPID = u'Harish.PSGui.1.0' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(MYAPPID)

        # we remoe the WindowStayOnTop flag
        self.setWindowFlags(Qt.FramelessWindowHint)


    def _set_com_ports(self):
        '''Set the COM ports drop downs'''
        # Set PS COM dro-down
        com_list = [desc for _, desc, _ in PS_COM_LIST]
        self.dd_pscom.com_list = com_list
        self.dd_pscom.setToolTip("Select PS 2000 COM port")
        self.dd_pscom.addItems(com_list)
        for i, com in enumerate(com_list):
            self.dd_rcom.setItemData(i, com, Qt.ToolTipRole)

        # Set Relay COM drop-down
        com_list = [desc for _, desc, _ in RELAY_COM_LIST]
        self.dd_rcom.com_list = com_list
        self.dd_rcom.setToolTip("Select Relay COM port")
        self.dd_rcom.addItems(com_list)
        for i, com in enumerate(com_list):
            self.dd_rcom.setItemData(i, com, Qt.ToolTipRole)


    def _attach_signals(self):
        '''Configure all buttons''' 
        self.timer.timeout.connect(self._timer_to)
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
        if self.dd_pscom.currentText():
            device = [com for com, desc, _ in PS_COM_LIST if desc == self.dd_pscom.currentText()]
            self.PSDev = PS2000(device[0])


    def dd_rcom_changed(self):
        '''Set tool tip for DropDown once value selected'''
        self.dd_rcom.setToolTip(self.dd_rcom.currentText())
        if self.dd_rcom.currentText():
            device = [com for com, desc, _ in RELAY_COM_LIST if desc == self.dd_rcom.currentText()]
            self.RelayDev = serial.Serial(device[0])


    def ps_toggled(self):
        '''PSButton click event'''
        if self.PSDev is None:
            self.b_ps.toggle()
            self.ui.Message.setText("**[INFO] Invalid Power Supply device (COM port)**")
            self.timer.start()
            return

        self.PSDev.set_remote(True)
        self.PSDev.set_output_on(on = bool(self.b_ps.isChecked()))
        self.PSDev.set_remote(False)


    def battery_toggled(self):
        '''BatteryButton click event'''
        if self.RelayDev is None:
            self.b_battery.toggle()
            self.ui.Message.setText("**[INFO] Invalid Relay device (COM port)**")
            self.timer.start()
            return

        relay = self.dd_battery.currentText()
        cmd = f'RL{relay[-1]}{int(self.b_battery.isChecked())}' if relay else ''
        self.RelayDev.write(self._gen_payload(cmd))


    def ig_toggled(self):
        '''IGButton click event'''
        if self.RelayDev is None:
            self.b_ig.toggle()
            self.ui.Message.setText("**[INFO] Invalid Relay device (COM port)**")
            self.timer.start()
            return

        relay = self.dd_ig.currentText()
        cmd = f'RL{relay[-1]}{int(self.b_ig.isChecked())}' if relay else ''
        self.RelayDev.write(self._gen_payload(cmd))


    def theme_clicked(self):
        '''Theme click event'''
        s2 = ''
        if self.b_theme.isChecked():
            with open(os.path.join(os.getcwd(), "stylesheets/light.css"), 'r') as f:
                s2 = f.read()
        with open(os.path.join(os.getcwd(), "stylesheets/stylesheet.css"), 'r') as s1:
            self.setStyleSheet(s1.read() + s2)


def error_handler(etype, value, tb):
    error_msg = ''.join(traceback.format_exception(etype, value, tb))
    # If error occurs showpopup and then close application
    QMessageBox.critical(Window, "Runtime Error", error_msg)
    app.exit(1)

if __name__ == "__main__":
    sys.excepthook = error_handler # Redirect std error

    app = QApplication(sys.argv)
    Window = UI()
    Window.activateWindow()
    app.exec_()
