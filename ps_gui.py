'''
ps_gui: Control PS2000 and Serial Relay board

Author: Harish Kathalingam (uif51939)
'''
import ctypes
import os
import sys
import traceback
from enum import Enum

import serial.tools.list_ports
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QPushButton, QComboBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, Qt, QTimer, QFile, QIODevice, QTextStream, QSettings

# Requires generation of layout.py and resources_rc.py
# read README.md
from layout import Ui_MainWindow
from ps2000 import PS2000


SETTING = QSettings("PSGui", "v1.0")
PROG_DIR = os.path.dirname(os.path.realpath(__file__)) #Canonical path to program's directory
RELAY_BAUD_RATE = 9600
PS_REGEX = r"^PS 2000"
RELAY_REGEX = fr"^(?!({PS_REGEX}))"
PS_COM_LIST = sorted(tuple(serial.tools.list_ports.grep(RELAY_REGEX)))
RELAY_COM_LIST = sorted(tuple(serial.tools.list_ports.grep(RELAY_REGEX)))


class Settings(str, Enum):
    '''Enums for settig paths'''
    THEME = "theme/styeshet"

    POWERSUPPLYCOM = "power_supply/com_port"
    ONVOLTAGE = "power_supply/on_voltage"
    OFFVOLTAGE = "power_supply/off_voltage"
    POWERSUPPLYTOGGLE = "power_supply/toggle_delay"

    REALYCOM = "relay/com_port"
    BATTERYRELAY = "relay/battery_realy"
    BATTERYTOGGLE = "relay/battery_toggle_delay"
    IGRELAY = "relay/ig_relay"
    IGTOGGLE = "relay/ig_toggle_delay"


class UI(QMainWindow):
    '''
    Class to setup MainWindow and related behaviors.
    '''
    def __init__(self):
        self.ps_device = None
        self.relay_device = None
        self.msg_timer = QTimer()
        self.msg_timer.setInterval(3000)
        self.msg_timer.setSingleShot(True)

        self.ps_toggle_timer = QTimer()
        self.battery_toggle_timer = QTimer()
        self.ig_toggle_timer = QTimer()
        self.ps_toggle_timer.setSingleShot(False)
        self.battery_toggle_timer.setSingleShot(False)
        self.ig_toggle_timer.setSingleShot(False)
        self.ps_toggle_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.battery_toggle_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.ig_toggle_timer.setTimerType(Qt.TimerType.PreciseTimer)

        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._set_window_property()

        # Load QSS
        if SETTING.value(Settings.THEME,""):
            self.ui.Theme.setChecked(True)
            self.theme_clicked()
        else:
            stylesheet = QFile(":/stylesheet/stylesheets/stylesheet.qss")
            stylesheet.open(QIODevice.ReadOnly)
            self.setStyleSheet(QTextStream(stylesheet).readAll())
            stylesheet.close()

        self.ui.TitleFrame.mouseMoveEvent = self.custMouseMoveEvent
        self._attach_signals()
        self._set_com_ports()
        self._set_realys()
        self._set_voltages()
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
        This function allows the window to be moved when
        the left mouse button is pressed and dragged.

        Parameters:
            e: represents the mouse event object.
        '''
        if a0.buttons() == Qt.LeftButton:
            self.move(self.pos() + a0.globalPos() - self.clickPosition)
            self.clickPosition = a0.globalPos()
            a0.accept()


    @staticmethod
    def _gen_payload(cmd:str):
        cmd = cmd + "\n\r"
        return cmd.encode()


    def _timer_to(self):
        self.ui.Message.clear()


    def _ps_toggle_to(self):
        '''Toggle Power supply once timer expires'''
        self.ui.PSButton.blockSignals(True)
        self.ui.PSButton.setChecked(not self.ui.PSButton.isChecked())
        self.ui.PSButton.blockSignals(False)

        self.ps_device.set_remote(True)
        voltage = int(self.ui.OnVoltage.text() if self.ui.PSButton.isChecked() else self.ui.OffVoltage.text())
        # When turnign on if On/OffVoltage is 0 we let hardware decide
        if self.ui.PSButton.isChecked() and voltage != 0:
            self.ps_device.set_voltage(voltage)
        self.ps_device.set_output_on(on = bool(self.ui.PSButton.isChecked()))
        self.ps_device.set_remote(False)


    def _relay_toggle_to(self, button: QPushButton, button_com: QComboBox):
        '''Toggle Relay switch once timer expires'''
        button.blockSignals(True)
        button.setChecked(not button.isChecked())
        button.blockSignals(False)

        relay = button_com.currentText()
        cmd = f"RL{relay[-1]}{int(button.isChecked())}" if relay else ""
        self.relay_device.write(self._gen_payload(cmd))


    def _set_window_property(self):
        '''Set application Icon'''
        # we make sure the window is opened at the topmost
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        app_icon = QIcon()
        app_icon.addFile(":/icons/icons/electric.png", QSize(24,24))
        APP.setWindowIcon(app_icon)

        # To show icon in taskbar
        MYAPPID = "Harish.PSGui.1.0" # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(MYAPPID)

        # we remoe the WindowStayOnTop flag
        self.setWindowFlags(Qt.FramelessWindowHint)


    def _set_com_ports(self):
        '''Set the COM ports drop downs'''
        # Set PS COM dro-down
        com_list = [desc for _, desc, _ in PS_COM_LIST]
        self.ui.PSCom.com_list = com_list
        self.ui.PSCom.setToolTip("Select PS 2000 COM port")
        self.ui.PSCom.addItems(com_list)

        # Set Tooltip for items in drop-down
        for i, com in enumerate(com_list):
            self.ui.RelayCom.setItemData(i, com, Qt.ToolTipRole)

        # Retrive from saved settings if exists
        if SETTING.value(Settings.POWERSUPPLYCOM) in com_list:
            self.ui.PSCom.setCurrentText(SETTING.value(Settings.POWERSUPPLYCOM))

        # Set Relay COM drop-down
        com_list = [desc for _, desc, _ in RELAY_COM_LIST]
        self.ui.RelayCom.com_list = com_list
        self.ui.RelayCom.setToolTip("Select Relay COM port")
        self.ui.RelayCom.addItems(com_list)

        # Set Tooltip for items in drop-down
        for i, com in enumerate(com_list):
            self.ui.RelayCom.setItemData(i, com, Qt.ToolTipRole)

        # Retrive from saved settings if exists
        if SETTING.value(Settings.REALYCOM) in com_list:
            self.ui.RelayCom.setCurrentText(SETTING.value(Settings.REALYCOM))


    def _set_realys(self):
        '''Set Battery and IG relay'''
        if not self.ui.RelayCom.currentText():
            return
        self.ui.BatteryCom.setCurrentText(SETTING.value(Settings.BATTERYRELAY, ""))
        self.ui.IGCom.setCurrentText(SETTING.value(Settings.IGRELAY, ""))


    def _set_voltages(self):
        '''Set Power supply On and Off voltages'''
        if not self.ui.PSCom.currentText():
            return
        self.ui.OnVoltage(SETTING.value(Settings.ONVOLTAGE).toInt(), 0)
        self.ui.OffVoltage(SETTING.value(Settings.OFFVOLTAGE).toInt(), 0)


    def _attach_signals(self):
        '''Configure all buttons''' 
        self.msg_timer.timeout.connect(self._timer_to)
        self.ps_toggle_timer.timeout.connect(self._ps_toggle_to)
        self.battery_toggle_timer.timeout.connect(lambda: self._relay_toggle_to(self.ui.BatteryButton, self.ui.BatteryCom))
        self.ig_toggle_timer.timeout.connect(lambda: self._relay_toggle_to(self.ui.IGButton, self.ui.IGCom))
        self.ui.Close.clicked.connect(self.close)
        self.ui.Minimise.clicked.connect(self.showMinimized)
        self.ui.Theme.clicked.connect(self.theme_clicked)
        self.ui.RelayCom.currentIndexChanged.connect(self.dd_rcom_changed)
        self.ui.PSCom.currentIndexChanged.connect(self.dd_pscom_changed)
        self.ui.PSButton.clicked.connect(self.ps_toggled)
        self.ui.BatteryCom.currentIndexChanged.connect(self.ui.BatteryCom.dd_changed)
        self.ui.BatteryButton.clicked.connect(self.battery_toggled)
        self.ui.IGCom.currentIndexChanged.connect(self.ui.IGCom.dd_changed)
        self.ui.IGButton.clicked.connect(self.ig_toggled)


    def dd_pscom_changed(self):
        '''Set tool tip for DropDown once value selected'''
        self.ui.PSCom.setToolTip(self.ui.PSCom.currentText())
        if self.ui.PSCom.currentText():
            device = [(com, desc) for com, desc, _ in PS_COM_LIST if desc == self.ui.PSCom.currentText()]
            self.ps_device = PS2000(device[0][0]) # Com port (com)
            SETTING.setValue(Settings.POWERSUPPLYCOM, device[0][1]) # description (desc)


    def dd_rcom_changed(self):
        '''Set tool tip for DropDown once value selected'''
        self.ui.RelayCom.setToolTip(self.ui.RelayCom.currentText())
        if self.ui.RelayCom.currentText():
            device = [(com, desc) for com, desc, _ in RELAY_COM_LIST if desc == self.ui.RelayCom.currentText()]
            self.relay_device = serial.Serial(device[0][0]) # Com port (com)
            SETTING.setValue(Settings.POWERSUPPLYCOM, device[0][1]) # description (desc)


    def ps_toggled(self):
        '''PSButton click event'''
        if self.ps_device is None:
            self.ui.PSButton.toggle()
            self.ui.Message.setText("**[INFO] Invalid Power Supply device (COM port)**")
            self.msg_timer.start()
            return

        self.ps_device.set_remote(True)
        voltage = int(self.ui.OnVoltage.text() if self.ui.PSButton.isChecked() else self.ui.OffVoltage.text())
        # When turnign on if On/OffVoltage is 0 we let hardware decide
        if self.ui.PSButton.isChecked() and voltage != 0:
            self.ps_device.set_voltage(voltage)
        self.ps_device.set_output_on(on = self.ui.PSButton.isChecked())
        self.ps_device.set_remote(False)

        if (not self.ps_toggle_timer.isActive()) and (self.ui.PSToggleDelay != 0):
            self.ps_toggle_timer.setInterval(self.ui.PSToggleDelay)
            self.ps_toggle_timer.start()

        if self.ps_toggle_timer.isActive():
            self.ui.Message.setText("**[INFO] Power supply auto-toggle stopped**")
            self.ps_toggle_timer.stop()


    def battery_toggled(self):
        '''BatteryButton click event'''
        if self.relay_device is None:
            self.ui.BatteryButton.toggle()
            self.ui.Message.setText("**[INFO] Invalid Relay device (COM port)**")
            self.msg_timer.start()
            return

        if not self.ui.BatteryCom.currentText():
            self.ui.Message.setText("**[INFO] Invalid Relay channel**")
            return

        relay = self.ui.BatteryCom.currentText()
        SETTING.setValue(Settings.BATTERYRELAY, self.ui.BatteryCom.currentText())
        cmd = f"RL{relay[-1]}{int(self.ui.BatteryButton.isChecked())}" if relay else ""
        self.relay_device.write(self._gen_payload(cmd))

        if (not self.battery_toggle_timer.isActive()) and (self.ui.BatteryToggleDelay != 0):
            self.battery_toggle_timer.setInterval(self.ui.BatteryToggleDelay)
            self.battery_toggle_timer.start()

        if self.battery_toggle_timer.isActive():
            self.ui.Message.setText("**[INFO] Battery auto-toggle stopped**")
            self.battery_toggle_timer.stop()


    def ig_toggled(self):
        '''IGButton click event'''
        if self.relay_device is None:
            self.ui.IGButton.toggle()
            self.ui.Message.setText("**[INFO] Invalid Relay device (COM port)**")
            self.msg_timer.start()
            return

        if not self.ui.IGCom.currentText():
            self.ui.Message.setText("**[INFO] Invalid Relay channel**")
            return

        relay = self.ui.IGCom.currentText()
        SETTING.setValue(Settings.IGRELAY, self.ui.IGCom.currentText())
        cmd = f"RL{relay[-1]}{int(self.ui.IGButton.isChecked())}" if relay else ""
        self.relay_device.write(self._gen_payload(cmd))

        if (not self.ig_toggle_timer.isActive()) and (self.ui.IGToggleDelay != 0):
            self.ig_toggle_timer.setInterval(self.ui.IGToggleDelay)
            self.ig_toggle_timer.start()

        if self.ig_toggle_timer.isActive():
            self.ui.Message.setText("**[INFO] IG auto-toggle stopped**")
            self.ig_toggle_timer.stop()


    def theme_clicked(self):
        '''Theme click event'''
        theme = ""
        if self.ui.Theme.isChecked():
            SETTING.setValue(Settings.THEME, ":/stylesheet/stylesheets/light.qss")
            file = QFile(":/stylesheet/stylesheets/light.qss")
            file.open(QIODevice.ReadOnly)
            theme = QTextStream(file).readAll()
            file.close()
        else:
            SETTING.setValue(Settings.THEME, "")

        stylesheet = QFile(":/stylesheet/stylesheets/stylesheet.qss")
        stylesheet.open(QIODevice.ReadOnly)
        self.setStyleSheet(QTextStream(stylesheet).readAll() + theme)
        stylesheet.close()


def error_handler(etype, value, tb):
    '''
    Custom Error handler:
        Make sure we show a popup on exception
        and gracefully exit the application
    '''
    error_msg = ''.join(traceback.format_exception(etype, value, tb))
    # If error occurs showpopup and then close application
    QMessageBox.critical(WINDOW, "Runtime Error", error_msg)
    APP.exit(1)

if __name__ == "__main__":
    sys.excepthook = error_handler # Redirect std error
    APP = QApplication(sys.argv)
    WINDOW = UI()
    WINDOW.activateWindow()
    APP.exec_()
