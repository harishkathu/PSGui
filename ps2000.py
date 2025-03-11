import struct
import serial.tools.list_ports

class PS2000(object):

    # set verbose to True to see all bytes
    verbose = False

    # defines
    PS_QUERY = 0x40
    PS_SEND = 0xC0

    # nominal values, required for all voltage and current calculations
    u_nom = 0
    i_nom = 0

    # open port upon initialization
    def __init__(self, port="/dev/ttyACM5"):
        # set timeout to 0.06s to guarantee minimum interval time of 50ms
        self.ser_dev = serial.Serial(
            port, timeout=0.06, baudrate=115200, parity=serial.PARITY_ODD
        )
        self.u_nom = self.get_nominal_voltage()
        self.i_nom = self.get_nominal_current()

    # close the door behind you
    def close(self):
        self.ser_dev.close()

    # construct telegram
    def _construct(self, type, node, obj, data):
        telegram = bytearray()
        telegram.append(0x30 + type)  # SD (start delimiter)
        telegram.append(node)  # DN (device node)
        telegram.append(obj)  # OBJ (object)
        if len(data) > 0:  # DATA
            telegram.extend(data)
            telegram[0] += len(data) - 1  # update length

        cs = 0
        for b in telegram:
            cs += b
        telegram.append(cs >> 8)  # CS0
        telegram.append(cs & 0xFF)  # CS1 (checksum)

        return telegram

    # compare checksum with header and data in response from device
    def _check_checksum(self, ans):
        cs = 0
        for b in ans[0:-2]:
            cs += b
        if (ans[-2] != (cs >> 8)) or (ans[-1] != (cs & 0xFF)):
            print("ERROR: checksum mismatch")
            return False
        else:
            return True

    # check for errors in response from device
    def _check_error(self, ans):
        if ans[2] != 0xFF:
            return False

        if ans[3] == 0x00:
            # this is used as an acknowledge
            return False

        return True

    # send one telegram, receive and check one response
    def _transfer(self, type, node, obj, data):
        telegram = self._construct(type, 0, obj, data)

        # send telegram
        self.ser_dev.write(telegram)

        # receive response (always ask for more than the longest answer)
        ans = self.ser_dev.read(100)

        self._check_checksum(ans)
        self._check_error(ans)

        return ans

    # get a binary object
    def _get_binary(self, obj):
        ans = self._transfer(self.PS_QUERY, 0, obj, "")

        return ans[3:-2]

    # set a binary object
    def _set_binary(self, obj, mask, data):
        ans = self._transfer(self.PS_SEND, 0, obj, [mask, data])

        return ans[3:-2]

    # get a string-type object
    def _get_string(self, obj):
        ans = self._transfer(self.PS_QUERY, 0, obj, "")

        return ans[3:-3].decode("ascii")

    # get a float-type object
    def _get_float(self, obj):
        ans = self._transfer(self.PS_QUERY, 0, obj, "")

        return struct.unpack(">f", ans[3:-2])[0]

    # get an integer object
    def _get_integer(self, obj):
        ans = self._transfer(self.PS_QUERY, 0, obj, "")

        return (ans[3] << 8) + ans[4]

    # set an integer object
    def _set_integer(self, obj, data):
        ans = self._transfer(self.PS_SEND, 0, obj, [data >> 8, data & 0xFF])

        return (ans[3] << 8) + ans[4]

    #
    # public functions ##################################################
    #

    # object 0
    def get_type(self):
        return self._get_string(0)

    # object 1
    def get_serial(self):
        return self._get_string(1)

    # object 2
    def get_nominal_voltage(self):
        return self._get_float(2)

    # object 3
    def get_nominal_current(self):
        return self._get_float(3)

    # object 4
    def get_nominal_power(self):
        return self._get_float(4)

    # object 6
    def get_article(self):
        return self._get_string(6)

    # object 8
    def get_manufacturer(self):
        return self._get_string(8)

    # object 9
    def get_version(self):
        return self._get_string(9)

    # object 19
    def get_device_class(self):
        return self._get_integer(19)

    # object 38
    def get_OVP_threshold(self):
        return self._get_integer(38)

    def set_OVP_threshold(self, u):
        return self._set_integer(38, u)

    # object 39
    def get_OCP_threshold(self):
        return self._get_integer(39)

    def set_OCP_threshold(self, i):
        return self._set_integer(39, i)

    # object 50
    def get_voltage_setpoint(self):
        v = self._get_integer(50)
        return self.u_nom * v / 25600

    def set_voltage(self, u):
        return self._set_integer(50, int(round((u * 25600.0) / self.u_nom)))

    # object 51
    def get_current_setpoint(self):
        i = self._get_integer(50)
        return self.i_nom * i / 25600

    def set_current(self, i):
        return self._set_integer(51, int(round((i * 25600.0) / self.i_nom)))

    # object 54
    def _get_control(self):
        return self._get_binary(54)

    def _set_control(self, mask, data):
        ans = self._set_binary(54, mask, data)

        # return True if command was acknowledged ("error 0")
        return ans[0] == 0xFF and ans[1] == 0x00

    def set_remote(self, remote=True):
        if remote:
            return self._set_control(0x10, 0x10)
        else:
            return self._set_control(0x10, 0x00)

    def set_local(self, local=True):
        return self.set_remote(not local)

    def set_output_on(self, on=True):
        if on:
            return self._set_control(0x01, 0x01)
        else:
            return self._set_control(0x01, 0x00)

    def set_output_off(self, off=True):
        return self.set_output_on(not off)

    def get_actual(self, print_state=False):
        ans = self._get_binary(71)

        actual = dict()
        actual["remote"] = True if ans[0] & 0x03 else False
        actual["local"] = not actual["remote"]
        actual["on"] = True if ans[1] & 0x01 else False
        actual["CC"] = True if ans[1] & 0x06 else False
        actual["CV"] = not actual["CC"]
        actual["OVP"] = True if ans[1] & 0x10 else False
        actual["OCP"] = True if ans[1] & 0x20 else False
        actual["OPP"] = True if ans[1] & 0x40 else False
        actual["OTP"] = True if ans[1] & 0x80 else False
        actual["v"] = self.u_nom * ((ans[2] << 8) + ans[3]) / 25600
        actual["i"] = self.i_nom * ((ans[4] << 8) + ans[5]) / 25600

        return actual
