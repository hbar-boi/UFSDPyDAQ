import pyvisa as pv
import time

ALLOWED_VOLTAGE_DELTA = 1.5 # Volt
TIME_DELAY = 0.5 # s

class HighVoltage():

    def __init__(self, board, resource = None):
        self.board = board
        self.connected = False
        self.rm = pv.ResourceManager()
        if resource == None:
            resource = self.promptResource()
        else:
            resource = self.rm.list_resources()[resource]

        try:
            self.handle = self.rm.open_resource(resource)
            self.connected = True
        except:
            return

        self.handle.query_delay = TIME_DELAY

        while True:
            status = self.getQuery("BDCTR")
            if "REMOTE" not in status:
                input("Please set power supply to REMOTE control and press enter...")
            else:
                break

        self.model = self.getQuery("BDNAME")

    def setQuery(self, param, channel, value = None):
        time.sleep(TIME_DELAY)
        if value == None:
            cmd = "$BD:{},CMD:SET,CH:{},PAR:{}".format(self.board,
                channel, param)
        else:
            cmd = "$BD:{},CMD:SET,CH:{},PAR:{},VAL:{}".format(self.board,
                channel, param, value)

        check(self.handle.query(cmd))

    def getQuery(self, param, channel = None):
        if channel == None:
            cmd = "$BD:{},CMD:MON,PAR:{}".format(self.board, param)
        else:
            cmd = "$BD:{},CMD:MON,CH:{},PAR:{}".format(self.board,
                channel, param)

        out = self.handle.query(cmd)
        if check(out):
            return out.split(",")[2].split(":")[1].rstrip()

    def enableChannel(self, channel):
        # Implement OFF check using status bits
        self.setQuery("ON", channel)

    def disableChannel(self, channel, confirm = True):
        self.setVoltage(channel, 0, confirm)
        self.setQuery("OFF", channel)

    def setVoltage(self, channel, value, confirm = True):
        self.setQuery("VSET", channel, value)
        if confirm:
            while True:
                delta = abs(self.getVoltage(channel) - value)
                if delta < ALLOWED_VOLTAGE_DELTA:
                    break

    def getVoltage(self, channel):
        return float(self.getQuery("VMON", channel))

    def getCurrent(self, channel):
        return float(self.getQuery("IMON", channel))

    def getModel(self):
        return self.model

    def close(self):
        self.handle.close()

    def promptResource(self):
        resources = self.rm.list_resources()
        num = len(resources)
        if num == 0:
            print("Fail!")
            print("No devices found, exiting.")
            exit()

        print("\nNo resource specified, please select one now...",
            end = "\n\n")

        for i, device in enumerate(resources):
            print("[{}]: {}".format(i, device),
                end = "\n" if i + 1 != num else "\n\n")

        def isValidResource(selected):
            if not str.isdigit(selected):
                return False
            selected = int(selected)
            return selected >= 0 and selected < num

        while True:
            selected = input("Resource number [0-{}]: ".format(num - 1))
            if isValidResource(selected):
                break

        return resources[int(selected)]

def check(msg):
    if "ERR" in msg:
        print("\nPower supply: an error occurred during the last operation.")
        return False
    else:
        return True

def __init__():
    pass

if __name__ == "__main__":
    print("I'm a module, please don't run me alone.")
    exit()
else:
    print("[High voltage ok] ", end = "")
