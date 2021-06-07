from modules import highvoltage, digitizer, tree

import configparser, sys, os, datetime, time
from pynput import keyboard

CONFIG_PATH = "config.ini"

DIGITIZER_MODELS = ["DT5742"]
HIGHVOLTAGE_MODELS = ["DT1471ET"]

CONFIG = {}

def init():
    # PyUSB acts weird if we try to connect the digitizer first...
    hv = connectHighVoltage()

    dgt = connectDigitizer()
    programDigitizer(dgt)
    dgtStatus = dgt.status()
    print("Digitizer status is {}, ".format(hex(dgtStatus)), end = "")
    if dgtStatus == 0x180:
        print("good!")
    else:
        print("something's wrong. Exiting.")
        exit()
    dgt.allocateEvent()
    dgt.mallocBuffer()

    return dgt, hv

PROGRESS_TICK = 4

def start(dgt, hv):
    global abort
    abort = False
    global events

    dir = "{} - {}".format(CONFIG["TRIGGER_BIAS"], now())
    dir = os.path.join(CONFIG["DATA_PATH"], dir)
    os.mkdir(dir)

    hv.enableChannel(CONFIG["SENSOR_CHANNEL"])
    hv.enableChannel(CONFIG["TRIGGER_CHANNEL"])
    print("\nWaiting for power supply... ", end = "")
    hv.setVoltage(CONFIG["TRIGGER_CHANNEL"], CONFIG["TRIGGER_BIAS"], True)
    print("Ready!")
    input("Press enter to start acquisition...")

    max = CONFIG["MAX_EVENTS"]
    for bias in CONFIG["SENSOR_BIAS"]:
        print("\nNow acquiring {} events with sensor bias at {} V".format(
            max, bias))

        print("Waiting for power supply... ", end = "")
        hv.setVoltage(CONFIG["SENSOR_CHANNEL"], bias, True)
        print("Ready!", end = "\n\n")

        progress = 0
        events = 0
        file = tree.TreeFile(str(bias))

        dgt.startAcquisition()
        while events <= max:
            events += acquire(dgt, file)
            if progress < events:
                print("Progress: {}/{} events...".format(events, max))
                progress += int(max / PROGRESS_TICK)

            if abort:
                print("Abort signal received, starting cleanup...",
                    end = "\n\n")
                dgt.stopAcquisition()
                file.close()
                cleanup(dgt, hv)
                exit()

        dgt.stopAcquisition()

        file.close()

    os.rename(dir, "{} to {}".format(dir, now()))

SAMPLING_FREQUENCIES = [5E3, 2.5E3, 1E3, 750] #MHz

def acquire(dgt, file):
    dgt.readData() # Update local buffer with data from the digitizer

    num = dgt.getNumEvents() # How many events in this block?
    for i in range(num):
        data, info = dgt.getEvent(i, True) # Get event data and info

        for j in range(18):
            group = int(j / 9)
            if data.GrPresent[group] != 1:
                continue # If this group was disabled then skip it

            channel = j - (9 * group)

            block = data.DataGroup[group]
            size = block.ChSize[channel]

            if channel == 8:
                file.setTrigger(group, block.DataChannel[channel], size)
            else:
                file.setChannel(j - group, block.DataChannel[channel], size)

        file.setFrequency(SAMPLING_FREQUENCIES[CONFIG["FREQUENCY"]])
        file.setEventLength(CONFIG["EVENT_LENGTH"])

        file.fill()

    return num

def cleanup(dgt, hv, file = None):
    print("\nDigitizer cleanup... ", end = "")
    dgt.stopAcquisition()
    dgt.freeEvent()
    dgt.freeBuffer()
    print("Done!")
    print("Closing connection to digitizer... ", end = "")
    dgt.close()
    print("Done!", end = "\n\n")
    print("Power supply cleanup... ", end = "")
    hv.disableChannel(CONFIG["SENSOR_CHANNEL"])
    hv.disableChannel(CONFIG["TRIGGER_CHANNEL"])
    print("Done!")
    print("Closing connection to power supply... ", end = "")
    hv.close()
    print("Done!", end = "\n\n")
    print("Exiting, goodbye...")

# ========================= HIGH VOLTAGE STUFF ================================

def connectHighVoltage():
    print("\nConnecting to power supply... ", end = "")
    hv = highvoltage.HighVoltage(CONFIG["HIGHVOLTAGE_ID"])
    if not hv.connected:
        print("Fail!")
        print("Couldn't connect to device, exiting.")
        exit()

    hvModel = hv.getModel()
    if not hvModel in HIGHVOLTAGE_MODELS:
        print("Fail!")
        print("This model is not supported, exiting.")
        exit()
    print("Done! Hello " + hvModel)
    return hv

# ========================= DIGITIZER STUFF ===================================

def connectDigitizer():
    print("\nConnecting to digitizer... ", end = "")
    dgt = digitizer.Digitizer(CONFIG["DIGITIZER_ID"])
    dgt.reset()
    dgtInfo = dgt.getInfo()
    dgtModel = str(dgtInfo.ModelName, "utf-8")
    if dgtModel not in DIGITIZER_MODELS:
        print("Fail!")
        print("This model is not supported, exiting.")
        exit()
    print("Done! Hello " + dgtModel)
    return dgt

def programDigitizer(device):
    print("Programming digitizer... ", end = "")
    # Data acquisition
    device.setSamplingFrequency(CONFIG["FREQUENCY"]) # Max frequency, 5 GHz
    device.setRecordLength(CONFIG["EVENT_LENGTH"]) # Max value for 742
    device.setMaxNumEventsBLT(1023) # Packet size for file transfer
    device.setAcquisitionMode(0) # Software controlled
    device.setExtTriggerInputMode(0) # Disable TRG IN trigger

    #device.writeRegister(0x8004, 1<<3) # Enable test pattern

    device.setFastTriggerMode(1) # Enable TR0 trigger
    device.setFastTriggerDigitizing(1) # Digitize TR0

    # Enable or disable groups
    device.setGroupEnableMask(0b11)

    # Positive polarity signals for both groups, unused but doesn't hurt
    device.setGroupTriggerPolarity(0, 0)
    device.setGroupTriggerPolarity(1, 0)

    device.setFastTriggerDCOffset(CONFIG["TRIGGER_BASELINE"])
    device.setFastTriggerThreshold(CONFIG["TRIGGER_THRESHOLD"])

    # Data processing
    if CONFIG["USE_INTERNAL_CORRECTION"]:
        device.loadCorrectionData(0) # Correction tables for 5 GHz operation
        device.enableCorrection()

    device.setPostTriggerSize(50) # Extra time after trigger
    print("Done!")

# ============================= UI SERVICES ===================================

BOOLEAN_PARAM = {"YES": True, "NO": False}

def parseConfig(path, config):
    parser = configparser.ConfigParser()
    parser.optionxform = lambda option: option
    parser.read(path)

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
        else:
            try:
                CONFIG[key] = int(CONFIG[key])
            except:
                pass

def keypress(key):
    global abort
    try:
        k = key.char
    except:
        k = key.name

    sys.stdout.write("\b")
    if k == "q":
        abort = True

def now():
    return datetime.datetime.fromtimestamp(
        time.time()).strftime('%Y-%m-%d %H:%M:%S')

if __name__ == "__main__":
    fullConfigPath = os.path.abspath(CONFIG_PATH)
    print("\nReading config file at {}... ".format(fullConfigPath), end = "")
    parseConfig(fullConfigPath, CONFIG)

    dgt, hv = init()

    if CONFIG["ENABLE_KEYBOARD"]:
        print("\nEnabling keyboard controls... ", end = "")
        controls = keyboard.Listener(on_press = keypress)
        controls.start()
        print("Done!")
        print("Press q to quit program")

    start(dgt, hv)
    cleanup(dgt, hv)
else:
    print("Please don't run me as a module...")
    exit()
