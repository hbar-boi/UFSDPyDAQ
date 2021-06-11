from modules import highvoltage, digitizer, tree

import configparser, sys, os, datetime, time
from pynput import keyboard

CONFIG_PATH = "config.ini"

DIGITIZER_MODELS = ["DT5742"]
HIGHVOLTAGE_MODELS = ["DT1471ET"]

PROGRESS_TICK = 4

class UFSDPyDAQ:

    def __init__(self, config):
        self.sensorChannel = config["SENSOR_CHANNEL"]
        self.triggerChannel = config["TRIGGER_CHANNEL"]

        self.triggerBias = config["TRIGGER_BIAS"]
        self.outputPath = config["DATA_PATH"]
        self.outputFile = config["FILENAME"]

        self.sensorBiases = config["SENSOR_BIAS"]

        self.maxEvents = config["MAX_EVENTS"]
        self.eventSize = config["EVENT_LENGTH"]
        self.mode = config["MODE"]
        self.frequency = config["FREQUENCY"]
        self.hvNumber = config["HIGHVOLTAGE_ID"]
        self.dgtNumber = config["DIGITIZER_ID"]
        self.triggerBaseline = config["TRIGGER_BASELINE"]
        self.triggerThresh = config["TRIGGER_THRESHOLD"]
        self.correct = config["USE_INTERNAL_CORRECTION"]

        # PyUSB acts weird if we try to connect the digitizer first...
        self.hv = connectHighVoltage()

        self.dgt = connectDigitizer()
        self.programDigitizer()
        status = self.dgt.status()
        print("Digitizer status is {}, ".format(hex(status)), end = "")
        if dgtStatus == 0x180:
            print("good!")
        else:
            print("something's wrong. Exiting.")
            exit()
        self.dgt.allocateEvent()
        self.dgt.mallocBuffer()

    def prepare(self):
        self.abort = False

        dir = os.path.join(self.outputPath)
        if not os.path.exists(dir):
            os.mkdir(dir)
        self.file = tree.TreeFile(dir, self.outputFile)

        SAMPLING_FREQUENCIES = [5E3, 2.5E3, 1E3, 750] # MHz
        self.file.setFrequency(SAMPLING_FREQUENCIES[self.frequency])
        self.file.setEventLength(self.eventSize)

        both = [self.sensorChannel, self.triggerChannel]

        self.hv.enableChannel(both)
        self.hv.setRampUp(both, 5) # V/s
        self.hv.setRampDown(both, 25) # V/s
        self.hvSetBlocking(self.triggerChannel, self.triggerBias)

        if input("Start acquisition? [y/n] ") == "n":
            return False
        else:
            return True

    def acquire(self):
        xStart = config["X_START"]
        xStep = config["X_STEP"]
        xStop = config["X_END"] + xStep

        yStart = config["Y_START"]
        yStep = config["Y_STEP"]
        yStop = config["Y_END"] + yStep

        for bias in self.sensorBiases:
            self.hvSetBlocking(self.sensorChannel, bias)
            self.file.setBias(bias)
            print("\nNow acquiring with sensor bias at {} V".format(bias))

            # Single point
            if self.mode == 0:
                self.acquirePoint(0, 0)
            # Grid acquisition
            elif self.mode == 1:
                for x in range(xStart, xStop, xStep):
                    for y in range(yStart, yStop, yStep):
                        self.acquirePoint(x, y)
            # Diagonal acquisition
            elif self.mode == 2:
                xRatioEnd = config["X_END"]
                yRatioEnd = config["Y_END"]
                aspectRatio = (yRatioEnd - yStart) / (xRatioEnd - xStart)

                for x in range(xStart, xStop, xStep):
                    y = yStart + ((x - xStart) * aspectRatio)
                    self.acquirePoint(x, y)

    def acquirePoint(self, x, y):
        print("\nNow acquiring {} events at (x = {}, y = {})".format(
            self.maxEvents, x, y))
        prompt = input("Press enter to continue, type 's' to skip or 'q' to quit... ")
        if prompt == "s":
            return
        elif prompt == "q":
            self.abort = True

        self.file.setPosition(x, y)

        events = 0
        self.dgt.startAcquisition()
        while True
            if self.abort:
                print("Abort signal received, starting cleanup...",
                    end = "\n\n")

                self.dgt.stopAcquisition()
                self.file.close()
                self.cleanup()
                exit()

            events += self.poll(events, bias)
            if events >= self.maxEvents:
                print("Acquired {}/{} events.".format(events, self.maxEvents))
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

    def hvSetBlocking(self, channel, bias):
        print("\nWaiting for power supply... ", end = "")
        self.hv.setVoltage(channel, bias, True)
        print("Ready!")

    def cleanup(self):
        self.file.close()
        print("\nDigitizer cleanup... ", end = "")
        self.dgt.stopAcquisition()
        self.dgt.freeEvent()
        self.dgt.freeBuffer()
        print("Done!")
        print("Closing connection to digitizer... ", end = "")
        self.dgt.close()
        print("Done!", end = "\n\n")
        print("Power supply cleanup... ", end = "")
        self.hv.disableChannel(self.sensorChannel)
        self.hv.disableChannel(self.triggerChannel)
        print("Done!")
        print("Closing connection to power supply... ", end = "")
        self.hv.close()
        print("Done!", end = "\n\n")
        print("Exiting, goodbye...")

# ========================= HIGH VOLTAGE STUFF ================================

    def connectHighVoltage(self):
        print("\nConnecting to power supply... ", end = "")
        self.hv = highvoltage.HighVoltage(self.hvNumber)
        if not self.hv.connected:
            print("Fail!")
            print("Couldn't connect to device, exiting.")
            exit()

        hvModel = self.hv.getModel()
        if not hvModel in HIGHVOLTAGE_MODELS:
            print("Fail!")
            print("This model is not supported, exiting.")
            exit()
        print("Done! Hello " + hvModel)

# ========================= DIGITIZER STUFF ===================================

    def connectDigitizer(self):
        print("\nConnecting to digitizer... ", end = "")
        self.dgt = digitizer.Digitizer(self.dgtNumber)
        self.dgt.reset()
        dgtInfo = self.dgt.getInfo()
        dgtModel = str(dgtInfo.ModelName, "utf-8")
        if dgtModel not in DIGITIZER_MODELS:
            print("Fail!")
            print("This model is not supported, exiting.")
            exit()
        print("Done! Hello " + dgtModel)

    def programDigitizer(self):
        print("Programming digitizer... ", end = "")
        # Data acquisition
        self.dgt.setSamplingFrequency(self.frequency) # Max frequency, 5 GHz
        self.dgt.setRecordLength(self.eventSize) # Max value for 742
        self.dgt.setMaxNumEventsBLT(1023) # Packet size for file transfer
        self.dgt.setAcquisitionMode(0) # Software controlled
        self.dgt.setExtTriggerInputMode(0) # Disable TRG IN trigger

        #device.writeRegister(0x8004, 1<<3) # Enable test pattern

        self.dgt.setFastTriggerMode(1) # Enable TR0 trigger
        self.dgt.setFastTriggerDigitizing(1) # Digitize TR0

        # Enable or disable groups
        self.dgt.setGroupEnableMask(0b11)

        # Positive polarity signals for both groups, unused but doesn't hurt
        self.dgt.setGroupTriggerPolarity(0, 0)
        self.dgt.setGroupTriggerPolarity(1, 0)

        self.dgt.setFastTriggerDCOffset(self.triggerBaseline)
        self.dgt.setFastTriggerThreshold(self.triggerThresh)

        # Data processing
        if correct:
            self.dgt.loadCorrectionData(0) # Correction tables for 5 GHz operation
            self.dgt.enableCorrection()

        self.dgt.setPostTriggerSize(50) # Extra time after trigger
        print("Done!")

# ============================= UI SERVICES ===================================

BOOLEAN_PARAM = {"YES": True, "NO": False}
MODE_PARAM = {"SINGLE": 0, "GRID": 1, "DIAG": 2}

def parseConfig(path):
    parser = configparser.ConfigParser()
    parser.optionxform = lambda option: option
    parser.read(path)

    CONFIG = {}

    for part in parser:
        section = parser[part]
        CONFIG.update(section)

    print("Done!", end = "\n\n")
    # Print params and make them machine-usable
    for key, param in CONFIG.items():
        print("{}: {}".format(key, param))
        if key == "SENSOR_BIAS":
            CONFIG[key] = [int(i) for i in CONFIG[key][1:-1].split(",")]
        elif param in BOOLEAN_PARAM.keys():
            CONFIG[key] = BOOLEAN_PARAM[CONFIG[key]]
        elif param in MODE_PARAM.keys():
            CONFIG[key] = MODE_PARAM[CONFIG[key]]
        else:
            try:
                CONFIG[key] = int(CONFIG[key])
            except:
                pass

    return CONFIG

if __name__ == "__main__":
    fullConfigPath = os.path.abspath(CONFIG_PATH)
    print("\nReading config file at {}... ".format(fullConfigPath), end = "")
    config = parseConfig(fullConfigPath)

    daq = UFSDPyDAQ(config)

    def keypress(key):
        global abort
        try:
            k = key.char
        except:
            k = key.name

        sys.stdout.write("\b")
        if k == "q":
            daq.abort = True

    print("\nEnabling keyboard controls... ", end = "")
    controls = keyboard.Listener(on_press = keypress)
    controls.start()
    print("Done!")

    if daq.prepare():
        daq.acquire()

    daq.cleanup()
else:
    print("Please don't run me as a module...")
    exit()
