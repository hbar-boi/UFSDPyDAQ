from ctypes import *
import urllib.parse

class CustomUnits(LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("A", c_double),
        ("MicrostepMode", c_uint)]

class Devices(LittleEndianStructure):
    pass

class MotorSettings(Structure):
	_fields_ = [
		("NomVoltage", c_uint),
		("NomCurrent", c_uint),
		("NomSpeed", c_uint),
		("uNomSpeed", c_uint),
		("EngineFlags", c_uint),
		("Antiplay", c_int),
		("MicrostepMode", c_uint),
		("StepsPerRev", c_uint)]

class MoveSettings(Structure):
	_fields_ = [
		("Speed", c_uint),
		("uSpeed", c_uint),
		("Accel", c_uint),
		("Decel", c_uint),
		("AntiplaySpeed", c_uint),
		("uAntiplaySpeed", c_uint),
		("MoveFlags", c_uint)]

class Position(Structure):
	_fields_ = [
		("Position", c_float),
		("EncPosition", c_longlong)]

SO_FILENAME = "libximc.so"
API = CDLL("/usr/lib/" + SO_FILENAME)

API.enumerate_devices.restype = POINTER(Devices)
API.get_device_name.restype = c_char_p

MAX_STEP_SPEED = 2000

class Axis():

    def __init__(self, stage, id):
        self.connected = False

        try:
            name = API.get_device_name(stage.devices, id)
            self.axis = API.open_device(name)
            self.stage = stage
        except:
            return

        self.connected = True

    def to(self, pos, wait = True):
        check(API.command_move_calb(self.axis, c_float(pos),
            byref(self.stage.units)))

        if wait:
            check(API.command_wait_for_stop(self.axis, 100))

    def setZero(self):
        check(API.command_zero(self.axis))

    def setMicrostep(self, value):
        settings = MotorSettings()

        check(API.get_engine_settings(self.axis, byref(settings)))
        settings.MicrostepMode = value
        check(API.set_engine_settings(self.axis, byref(settings)))

    def setSpeed(self, value):
        if value > MAX_STEP_SPEED:
            print("Speed is too high!")
            return

        settings = MoveSettings()
        check(API.get_move_settings(self.axis, byref(settings)))
        settings.Speed = int(value)
        check(API.set_move_settings(self.axis, byref(settings)))

    def getPosition(self):
        position = Position()
        check(API.get_position_calb(self.axis, byref(position),
            byref(self.stage.units)))

        return position.Position

    def close(self):
        handle = cast(self.axis, POINTER(c_int))
        check(API.close_device(byref(handle)))

class Stage():

    def __init__(self, ids):
        self.devices = API.enumerate_devices(0x01, b"addr=")
        self.connected = True

        self.axes = []
        for id in ids:
            axis = Axis(self, id)
            self.connected &= axis.connected
            self.axes.append(axis)

        if not self.connected:
            return

        self.units = CustomUnits()
        self.units.A = 0.31 # um/step
        self.units.MicrostepMode = 0x04 # 1/8 usteps

        self.setZero()
        self.setMicrostep(0x04) # 1/8 usteps

    def getDeviceCount(self):
        return API.get_device_count(self.devices)

    def setZero(self):
        for axis in self.axes:
            axis.setZero()

    def setStepSpeed(self, value):
        for axis in self.axes:
            axis.setStepSpeed(value)

    def setMicrostep(self, value):
        for axis in self.axes:
            axis.setMicrostep(value)

    def to(self, x, y, wait = True):
        self.axes[0].to(x, False)
        self.axes[1].to(y, wait)

    def getPosition(self):
        return [axis.getPosition() for axis in self.axes]

    def close(self):
        for axis in self.axes:
            axis.close()

def check(code):
    if code != 0:
        print("\nStage: an error occurred during the last operation. Code: " + str(code))

if __name__ == "__main__":
    print("I'm a module, please don't run me alone.")
    exit()
else:
    print("[Stage ok] ", end = "")
