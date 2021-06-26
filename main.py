from modules import highvoltage, digitizer, tree, stage

import configparser, sys, os, datetime, time
from pynput import keyboard

CONFIG_PATH = "config.ini"

DIGITIZER_MODELS = ["DT5742"]
HIGHVOLTAGE_MODELS = ["DT1471ET"]

PROGRESS_TICK = 4

class UFSDPyDAQ:

    def __init__(self, config):

        self.acqConfig = config["ACQUISITION"]

        self.maxEvents = self.acqConfig["MAX_EVENTS"]
        self.mode = self.acqConfig["MODE"]
        self.outputPath = self.acqConfig["DATA_PATH"]
        self.outputFile = self.acqConfig["FILENAME"]

        self.dgtConfig = config["DIGITIZER"]
        self.hvConfig = config["HIGHVOLTAGE"]
        self.stageConfig = config["STAGE"]

        # PyUSB acts weird if we try to connect the digitizer first...
        self.connectHighVoltage()

        self.connectStage()
        self.programStage()

        self.connectDigitizer()
        self.programDigitizer()
        status = self.dgt.status()
        print("Digitizer status is {}, ".format(hex(status)), end = "")
        if status == 0x180:
            formatted(" good!", FORMAT_OK)
        else:
            formatted("something's wrong. Exiting.", FORMAT_ERROR)
            exit()
        self.dgt.allocateEvent()
        self.dgt.mallocBuffer()

    def prepare(self):
        dir = os.path.join(self.outputPath)
        if not os.path.exists(dir):
            os.mkdir(dir)
        self.file = tree.TreeFile(dir, self.outputFile)

        SAMPLING_FREQUENCIES = [5E3, 2.5E3, 1E3, 750] # MHz
        self.file.setFrequency(SAMPLING_FREQUENCIES[self.frequency])
        self.file.setEventLength(self.eventSize)

        both = [self.sensorChannel, self.triggerChannel]

        self.hv.enableChannel(self.biasChannels)
        self.hvSetBlocking(self.triggerChannel, self.triggerBias)

        if input("Start acquisition? [y/n] ") == "n":
            return False
        else:
            return True

    def acquire(self):
        xStart = self.acqConfig["X_START"]
        xStep = self.acqConfig["X_STEP"]
        xStop = self.acqConfig["X_END"] + xStep

        yStart = self.acqConfig["Y_START"]
        yStep = self.acqConfig["Y_STEP"]
        yStop = self.acqConfig["Y_END"] + yStep

        for bias in self.sensorBiases:
            self.hvSetBlocking(self.sensorChannel, bias)
            self.file.setBias(bias)
            formatted("\nNow acquiring with sensor bias at {} V".format(bias),
                FORMAT_NOTE)

            if not self.askSkipQuit(self.autoHv):
                continue
            # Single point
            if self.mode == 0:
                self.acquirePoint(xStart, yStart)
            # Grid acquisition
            elif self.mode == 1:
                for x in range(xStart, xStop, xStep):
                    for y in range(yStart, yStop, yStep):
                        self.acquirePoint(x, y)
            # Diagonal acquisition
            elif self.mode == 2:
                xRatioEnd = self.acqConfig["X_END"]
                yRatioEnd = self.acqConfig["Y_END"]
                aspectRatio = (yRatioEnd - yStart) / (xRatioEnd - xStart)

                for x in range(xStart, xStop, xStep):
                    y = yStart + ((x - xStart) * aspectRatio)
                    self.acquirePoint(x, y)
            elif self.mode == 3:
                xList = self.acqConfig["X_LIST"]
                yList = self.acqConfig["Y_LIST"]
                if len(xList) != len(yList):
                    formatted("Lists have to be the same length... Exiting",
                        FORMAT_ERROR)
                    exit()

                points = list(zip(xList, yList))
                for point in points:
                    self.acquirePoint(point[0], point[1])

    def acquirePoint(self, x, y):
        formatted("\nNow acquiring {} events at (x = {}, y = {})".format(
            self.maxEvents, x, y), FORMAT_NOTE, "")

        self.stage.to2d(x, y, True)
        if self.autoStage:
            position = self.stage.getPosition()
            formatted("Current position is (x = {:.3f}, y = {:.3f})".format(
                position[0], position[1]), FORMAT_NOTE)

        if not self.askSkipQuit(self.autoStage):
            return
        self.file.setPosition(x, y)

        events = 0
        self.dgt.startAcquisition()
        while True:
            events += self.poll(events)
            if events >= self.maxEvents:
                formatted("Acquired {}/{} events.".format(events,
                    self.maxEvents), FORMAT_OK, "")
                break
        self.dgt.stopAcquisition()

        self.file.write()

    def poll(self, taken):
        self.dgt.readData() # Update local buffer with data from the digitizer

        size = self.dgt.getNumEvents() # How many events in this block?
        remaining = min(size, self.maxEvents - taken)
        for i in range(remaining):
            data, info = self.dgt.getEvent(i, True) # Get event data and info

            for j in range(18):
                group = int(j / 9)
                if data.GrPresent[group] != 1:
                    continue # If this group was disabled then skip it

                channel = j - (9 * group)
                block = data.DataGroup[group]
                size = block.ChSize[channel]

                if channel == 8:
                    self.file.setTrigger(group,
                        block.DataChannel[channel], size)
                else:
                    self.file.setChannel(j - group,
                        block.DataChannel[channel], size)

            self.file.fill()
        return remaining

    def cleanup(self):
        self.file.close()

        formatted("\nDigitizer cleanup... ", FORMAT_NOTE, "")
        self.dgt.stopAcquisition()
        self.dgt.freeEvent()
        self.dgt.freeBuffer()
        formatted("Done!", FORMAT_OK)

        formatted("Closing connection to digitizer... ", FORMAT_NOTE, "")
        self.dgt.close()
        formatted("Done!", FORMAT_OK)

        if self.autoHv:
            formatted("Power supply cleanup... ", FORMAT_NOTE, "")
            both = [self.sensorChannel, self.triggerChannel]
            self.hv.disableChannel(both)
            formatted("Done!", FORMAT_OK)

            formatted("Closing connection to power supply... ", FORMAT_NOTE, "")
            self.hv.close()
            formatted("Done!", FORMAT_OK)

        if self.autoStage:
            formatted("Stage cleanup... ", FORMAT_NOTE, "")
            self.stage.to2d(0, 0)
            formatted("Done!", FORMAT_OK)

            formatted("Closing connection to stage...", FORMAT_NOTE, "")
            self.stage.close()
            formatted("Done!", FORMAT_OK)

        formatted("Exiting, goodbye...", FORMAT_NOTE, "")

# ============================ STAGE STUFF ====================================

    def connectStage(self):
        self.autoStage = not self.stageConfig["MANUAL"]
        if not self.autoStage:
            self.stage = Nothing()
            return

        formatted("Connecting to stage...", FORMAT_NOTE, "")
        self.stage = stage.Stage({
            "x": self.stageConfig["X_AXIS"],
            "y": self.stageConfig["Y_AXIS"]})

        if not self.stage.connected:
            formatted("Fail! Couldn't connect to stage, exiting.",
                FORMAT_ERROR)
            exit()

        formatted("Done! Hello stage...", FORMAT_OK)

    def programStage(self):
        self.stage.setSpeed(self.stageConfig["SPEED"])

# ========================= HIGH VOLTAGE STUFF ================================

    def connectHighVoltage(self):
        self.sensorChannel = self.hvConfig["SENSOR_CHANNEL"]
        self.triggerChannel = self.hvConfig["TRIGGER_CHANNEL"]
        self.triggerBias = self.hvConfig["TRIGGER_BIAS"]
        self.sensorBiases = self.hvConfig["SENSOR_BIAS"]

        self.biasChannels = [self.sensorChannel, self.triggerChannel]

        self.autoHv = not self.hvConfig["MANUAL"]
        if not self.autoHv:
            self.hv = Nothing()
            return

        formatted("\nConnecting to power supply... ", FORMAT_NOTE, end = "")
        self.hv = highvoltage.HighVoltage(self.hvConfig["HIGHVOLTAGE_ID"])
        if not self.hv.connected:
            formatted("Fail!", "Couldn't connect to device, exiting.",
                FORMAT_ERROR)
            exit()

        hvModel = self.hv.getModel()
        if not hvModel in HIGHVOLTAGE_MODELS:
            formatted("Fail! This model is not supported, exiting.",
                FORMAT_ERROR)
            exit()
        formatted("Done! Hello " + hvModel, FORMAT_OK)

    def programHighVoltage(self):
        self.hv.setRampUp(self.biasChannels, self.hvConfig["RAMP_UP_RATE"])
        self.hv.setRampDown(self.biasChannels, self.hvConfig["RAMP_DOWN_RATE"])

    def hvSetBlocking(self, channel, bias):
        if self.autoHv:
            formatted("\nWaiting for power supply... ", FORMAT_NOTE, "")
            self.hv.setVoltage(channel, bias, True)
            formatted("Ready!", FORMAT_OK)

# ========================= DIGITIZER STUFF ===================================

    def connectDigitizer(self):
        self.eventSize = self.dgtConfig["EVENT_LENGTH"]
        self.frequency = self.dgtConfig["FREQUENCY"]

        formatted("Connecting to digitizer... ", FORMAT_NOTE, "")
        self.dgt = digitizer.Digitizer(self.dgtConfig["DIGITIZER_ID"])
        if not self.dgt.connected:
            formatted("Fail! Couldn't connect to device, exiting.",
                FORMAT_ERROR)
            exit()

        self.dgt.reset()
        dgtInfo = self.dgt.getInfo()
        dgtModel = str(dgtInfo.ModelName, "utf-8")
        if dgtModel not in DIGITIZER_MODELS:
            formatted("Fail! This model is not supported, exiting.",
                FORMAT_ERROR)
            exit()

        formatted("Done! Hello " + dgtModel, FORMAT_OK)

    def programDigitizer(self):
        formatted("Programming digitizer... ", FORMAT_NOTE, end = "")
        # Data acquisition
        self.dgt.setSamplingFrequency(self.frequency)
        self.dgt.setRecordLength(self.eventSize)
        self.dgt.setMaxNumEventsBLT(1023) # Packet size for file transfer
        self.dgt.setAcquisitionMode(0) # Software controlled
        self.dgt.setExtTriggerInputMode(0) # Disable TRG IN trigger

        # device.writeRegister(0x8004, 1<<3) # Enable test pattern

        self.dgt.setFastTriggerMode(1) # Enable TR0 trigger
        self.dgt.setFastTriggerDigitizing(1) # Digitize TR0

        # Enable or disable groups
        self.dgt.setGroupEnableMask(0b11)

        if "CHANNEL_DC_OFFSET" in self.dgtConfig:
            for i in range(16):
                self.dgt.setChannelDCOffset(i,
                    self.dgtConfig["CHANNEL_DC_OFFSET"])

        # Positive polarity signals for both groups, unused but doesn't hurt
        self.dgt.setGroupTriggerPolarity(0, 0)
        self.dgt.setGroupTriggerPolarity(1, 0)

        self.dgt.setFastTriggerDCOffset(
            self.dgtConfig["TRIGGER_BASELINE"])
        self.dgt.setFastTriggerThreshold(
            self.dgtConfig["TRIGGER_THRESHOLD"])

        # Data processing
        if self.dgtConfig["USE_INTERNAL_CORRECTION"]:
            # Correction tables for 5 GHz operation
            self.dgt.loadCorrectionData(0)
            self.dgt.enableCorrection()

        self.dgt.setPostTriggerSize(
            self.dgtConfig["POST_TRIGGER_DELAY"]) # Extra time after trigger
        formatted("Done!", FORMAT_OK)

    def askSkipQuit(self, bypass):
        if bypass:
            return True

        prompt = input("Press enter to continue, type 's' to skip or 'q' to quit... ")
        if prompt == "s":
            return False
        elif prompt == "q":
            self.dgt.stopAcquisition()

            self.cleanup()
            exit()
        return True

# ============================= UI SERVICES ===================================

FORMAT_ERROR = "\033[91m"
FORMAT_WARNING = "\033[93m"
FORMAT_NOTE = "\033[94m"
FORMAT_OK = "\033[92m"

def formatted(string, format, end = "\n"):
    print(format, end = "")
    sys.stdout.write("\b")
    print(string, "\033[0m", end)

class Nothing():

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, attr):
        def bye(*args, **kwargs):
            pass
        return bye

BOOLEAN_PARAM = {"YES": True, "NO": False}
MODE_PARAM = {"SINGLE": 0, "GRID": 1, "DIAG": 2, "LIST": 3}
KEYS_ARRAY = ["SENSOR_BIAS", "X_LIST", "Y_LIST"]

def loadConfig(path):
    parser = configparser.ConfigParser()
    parser.optionxform = lambda option: option
    parser.read(path)

    def parse(key):
        # Print params and make them machine-usable
        config = {}
        formatted("\n[{}]".format(key), FORMAT_NOTE)
        for k, param in parser[key].items():
            print("{}: {}".format(k, param))
            if k in KEYS_ARRAY:
                config[k] = [int(i) for i in param[1:-1].split(",")]
            elif param in BOOLEAN_PARAM.keys():
                config[k] = BOOLEAN_PARAM[param]
            elif param in MODE_PARAM.keys():
                config[k] = MODE_PARAM[param]
            else:
                try:
                    config[k] = int(param)
                except:
                    config[k] = str(param)

        return config

    config = {key:parse(key) for key in parser.sections()}
    formatted("\nDone!", FORMAT_OK)
    return config

if __name__ == "__main__":
    fullConfigPath = os.path.abspath(CONFIG_PATH)
    print("\nReading config file at {}... ".format(fullConfigPath))
    config = loadConfig(fullConfigPath)

    daq = UFSDPyDAQ(config)

    if daq.prepare():
        daq.acquire()

    daq.cleanup()
else:
    print("Please don't run me as a module...")
    exit()
