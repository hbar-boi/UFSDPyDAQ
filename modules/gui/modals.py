from modules import backend
from modules.gui.config import *
import wx, copy

class HvProgramModal(wx.Dialog):

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title = "High voltage settings",
            size = (300, 157))

        panel = wx.Panel(self)

        wx.StaticText(panel, size = (300, -1), pos = (10, 5),
            label = "Sensor bias channel")
        self.hvSensChn = wx.SpinCtrl(panel, max = 3, value = "0", size = (134, -1),
            pos = (10, 30))
        wx.StaticText(panel, size = (300, -1), pos = (154, 5),
            label = "Trigger bias channel")
        self.hvTrgChn = wx.SpinCtrl(panel, max = 3, value = "1", size = (134, -1),
            pos = (154, 30))

        okBtn = wx.Button(panel, pos = (189, 75), size = (100, -1),
            label = "Apply")
        self.okBtnId = okBtn.GetId()
        backBtn = wx.Button(panel, pos = (10, 75), size = (100, -1),
            label = "Cancel")

        self.SetAffirmativeId(okBtn.GetId())
        self.SetEscapeId(backBtn.GetId())

    def ShowInCenter(self):
        getIfConfigured("SENSOR_CHANNEL", self.hvSensChn)
        getIfConfigured("TRIGGER_CHANNEL", self.hvTrgChn)

        ret = self.ShowModal()
        self.Center()
        return (ret == self.okBtnId)

class DgtChnOffsetModal(wx.Dialog):

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title = "Channels DC offset",
            size = (608, 425))

        self.parent = parent
        panel = wx.Panel(self)

        self.dgtFirstGrpOfst = wx.StaticBox(panel, label = "First group",
            pos = (10, 5), size = (588, 160), style = wx.ALIGN_CENTER)
        self.dgtSecondGrpOfst = wx.StaticBox(panel, label = "Second group",
            pos = (10, 170), size = (588, 160), style = wx.ALIGN_CENTER)

        self.dgtChnOffsets = []
        parent = self.dgtFirstGrpOfst
        yShift = 0
        for i in range(4):
            if i == 2:
                yShift -= 130
                parent = self.dgtSecondGrpOfst
            for j in range(4):
                xShift = 144 * j
                wx.StaticText(parent, size = (300, -1),
                    pos = (10 + xShift, 5 + yShift),
                    label = "Channel {}".format((i * 4) + j))
                self.dgtChnOffsets.append(
                    wx.SpinCtrl(parent, min = 0, max = 65535, value = "0",
                        size = (134, -1), pos = (10 + xShift, 30 + yShift)))

            yShift += 65

        okBtn = wx.Button(panel, pos = (498, 342), size = (100, -1),
            label = "Apply")
        self.okBtnId = okBtn.GetId()
        backBtn = wx.Button(panel, pos = (10, 342), size = (100, -1),
            label = "Cancel")

        self.SetAffirmativeId(okBtn.GetId())
        self.SetEscapeId(backBtn.GetId())

    def ShowInCenter(self, event = None):
        global ENABLED_CHANNELS
        enableIndex = ENABLED_CHANNELS[0].index(
            self.parent.dgtEnChns.GetValue())
        enableMask = ENABLED_CHANNELS[1][enableIndex]

        self.dgtFirstGrpOfst.Enable(enableMask & 0b01)
        self.dgtSecondGrpOfst.Enable(enableMask & 0b10)

        options = backend.CONFIG
        initOfstKey = "CHANNEL_OFFSET"
        if initOfstKey in options.keys():
            initOfst = copy.copy(options[initOfstKey])
            self.dgtChnNewOfst = initOfst if len(initOfst) == 16 else [0] * 16

            for i, o in enumerate(self.dgtChnNewOfst):
                self.dgtChnOffsets[i].SetValue(str(o))

        ret = self.ShowModal()
        self.Center()
        return (ret == self.okBtnId)

class DgtProgramModal(wx.Dialog):

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title = "Digitizer settings",
            size = (300, 377))

        panel = wx.Panel(self)
        self.dgtChnOffsetModal = DgtChnOffsetModal(self)

        global SAMPLING_FREQUENCIES
        wx.StaticText(panel, size = (300, -1), pos = (10, 5),
            label = "Sampling frequency")
        self.dgtFreq = wx.ComboBox(panel, style = wx.CB_READONLY,
            size = (134, -1), pos = (10, 30), choices = SAMPLING_FREQUENCIES[0],
            value = SAMPLING_FREQUENCIES[0][0])
        self.dgtFreq.Bind(wx.EVT_COMBOBOX, self.updateMaxDelay)
        wx.StaticText(panel, size = (300, -1), pos = (154, 5),
            label = "Max events in BLT")
        self.dgtBLTEvts = wx.SpinCtrl(panel, min = 1, max = 1023, value = "1023",
            size = (134, -1), pos = (154, 30))

        global EVENT_SAMPLES
        wx.StaticText(panel, size = (300, -1), pos = (10, 70),
            label = "Samples per event")
        self.dgtEvtSamples = wx.ComboBox(panel, style = wx.CB_READONLY,
            size = (134, -1), pos = (10, 95), choices = EVENT_SAMPLES[0],
            value = EVENT_SAMPLES[0][3])
        self.dgtEvtSamples.Bind(wx.EVT_COMBOBOX, self.updateMaxDelay)
        wx.StaticText(panel, size = (300, -1), pos = (154, 70),
            label = "Trigger delay (ns)")
        self.dgtTrgDelay = wx.SpinCtrl(panel, min = 0, size = (134, -1),
            pos = (154, 95), value = "0")

        global ENABLED_CHANNELS
        wx.StaticText(panel, size = (300, -1), pos = (10, 135),
            label = "Enabled channels")
        self.dgtEnChns = wx.ComboBox(panel, style = wx.CB_READONLY,
            size = (134, -1), pos = (10, 160), choices = ENABLED_CHANNELS[0],
            value = ENABLED_CHANNELS[0][2])
        wx.StaticText(panel, size = (300, -1), pos = (154, 135),
            label = "Channels DC offset")
        self.dgtChnOfst = wx.Button(panel, pos = (154, 160), size = (134, -1),
            label = "Edit")
        self.dgtChnOfst.Bind(wx.EVT_BUTTON, self.promptChnOffset)

        wx.StaticText(panel, size = (300, -1), pos = (10, 200),
            label = "Trigger offset")
        self.dgtTrgOfst = wx.SpinCtrl(panel, min = 0, max = 65535, value = "0",
            size = (134, -1), pos = (10, 225))
        wx.StaticText(panel, size = (300, -1), pos = (154, 200),
            label = "Trigger DC threshold")
        self.dgtTrgThresh = wx.SpinCtrl(panel, min = 0, max = 65535, value = "0",
            size = (134, -1), pos = (154, 225))

        wx.StaticText(panel, size = (300, -1), pos = (33, 268),
            label = "Use digitizer internal data correction")
        self.dgtDataCorr = wx.CheckBox(panel, size = (300, -1), pos = (10, 267))

        okBtn = wx.Button(panel, pos = (189, 295), size = (100, -1),
            label = "Apply")
        self.okBtnId = okBtn.GetId()
        backBtn = wx.Button(panel, pos = (10, 295), size = (100, -1),
            label = "Cancel")

        self.SetAffirmativeId(okBtn.GetId())
        self.SetEscapeId(backBtn.GetId())

    def updateMaxDelay(self, event = None):
        self.dgtTrgDelay.SetMax(self.getMaxDelay())

    def getMaxDelay(self, freqIndex = None, evtsIndex = None):
        if freqIndex == None:
            global SAMPLING_FREQUENCIES
            freqIndex = SAMPLING_FREQUENCIES[0].index(
                self.dgtFreq.GetValue())

        if evtsIndex == None:
            global EVENT_SAMPLES
            evtsIndex = EVENT_SAMPLES[0].index(
                self.dgtEvtSamples.GetValue())

        frequency = SAMPLING_FREQUENCIES[1][freqIndex]
        samples = EVENT_SAMPLES[1][evtsIndex]
        return int(1E9 * samples / frequency)

    def promptChnOffset(self, event):
        modal = self.dgtChnOffsetModal
        if modal.ShowInCenter():
            for i, o in enumerate(modal.dgtChnOffsets):
                modal.dgtChnNewOfst[i] = o.GetValue()

    def ShowInCenter(self):
        global SAMPLING_FREQUENCIES
        getIfConfigured("SAMPLING_FREQUENCY", self.dgtFreq, SAMPLING_FREQUENCIES[0])
        getIfConfigured("BLT_EVENTS_MAX", self.dgtBLTEvts)
        global EVENT_SAMPLES
        getIfConfigured("SAMPLES_PER_EVENT", self.dgtEvtSamples, EVENT_SAMPLES[0])

        self.updateMaxDelay()

        getIfConfigured("POST_TRIGGER_DELAY", self.dgtTrgDelay)
        global ENABLED_CHANNELS
        getIfConfigured("ENABLED_GROUPS", self.dgtEnChns, ENABLED_CHANNELS[0])
        getIfConfigured("TRIGGER_BASELINE", self.dgtTrgOfst)
        getIfConfigured("TRIGGER_THRESHOLD", self.dgtTrgThresh)
        getIfConfigured("USE_INTERNAL_CORRECTION", self.dgtDataCorr)

        ret = self.ShowModal()
        self.Center()
        return (ret == self.okBtnId)

class FailModal(wx.Dialog):
    def __init__(self, parent, title):
        wx.Dialog.__init__(self, parent, title = title, size = (300, 160))

        panel = wx.Panel(self)

        self.alert = wx.StaticText(panel, size = (-1, 200), pos = (10, 10))

        okBtn = wx.Button(panel, pos = (498, 342), size = (100, -1),
            label = "Retry")
        self.okBtnId = okBtn.GetId()
        backBtn = wx.Button(panel, pos = (10, 342), size = (100, -1),
            label = "Cancel")

        self.SetAffirmativeId(okBtn.GetId())
        self.SetEscapeId(backBtn.GetId())

    def ShowInCenter(self, text):
        self.alert.SetLabel(text)
        self.alert.Wrap(280)

        ret = self.ShowModal()
        self.Center()
        return (ret == self.okBtnId)

def getIfConfigured(key, control, fromArray = None):
    keys = backend.CONFIG.keys()
    if key in keys:
        try:
            data = backend.CONFIG[key]
            if fromArray != None:
                data = fromArray[data]
            control.SetValue(data)
        except:
            pass

def saveToConfig(key, control, fromArray = None, toArray = None):
    value = control.GetValue()
    if fromArray == None:
        res = int(value)
    else:
        index = fromArray.index(value)
        if toArray == None:
            res = index
        else:
            res = toArray[index]

    backend.CONFIG[key] = res
