def init():
    app = wx.App(False)
    main = MainWindow()

    app.MainLoop()

class MainWindow(wx.Frame):

    def __init__(self):
        style = wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER
        wx.Frame.__init__(self, None, title = "UFSDPyDAQ", size = (635, 590), style = style)

        self.hvProgramModal = HvProgramModal(self)
        self.hvFailModal = FailModal(self, "High voltage alert")
        self.dgtProgramModal = DgtProgramModal(self)
        panel = wx.Panel(self)

        # ======================== HIGH VOLTAGE INIT ==========================
        self.hvBox = wx.StaticBox(panel, label = "High voltage",
            pos = (10, 5), size = (300, 230), style = wx.ALIGN_CENTER)

        wx.StaticText(self.hvBox, label = "Device port", style = wx.ALIGN_LEFT,
            size = (280, -1), pos = (10, 5))

        self.hvPort = wx.ComboBox(self.hvBox, style = wx.CB_READONLY,
            size = (134, -1), pos = (10, 30))
        self.hvRefresh = wx.Button(self.hvBox, label = "Refresh",
            pos = (154, 30), size = (134, -1))
        self.hvRefresh.Bind(wx.EVT_BUTTON, self.populateHvPorts)

        self.hvDevPanel = wx.Panel(self.hvBox, pos = (0, 70), size = (290, 144))
        self.hvDevText = wx.StaticText(self.hvDevPanel, label = "Device ID",
            style = wx.ALIGN_LEFT, size = (280, -1), pos = (10, 0))
        self.hvDevice = wx.SpinCtrl(self.hvDevPanel, size = (134, -1), pos = (10, 25))
        self.hvConnect = wx.Button(self.hvDevPanel, pos = (154, 25), size = (134, -1))

        self.hvProgram = wx.Button(self.hvBox, pos = (10, 140),
            size = (278, -1), label = "Setup")
        self.hvProgram.Bind(wx.EVT_BUTTON, self.programHv)

        self.hvStatus = wx.StaticText(self.hvBox, style = wx.ALIGN_LEFT,
            size = (280, -1), pos = (10, 185))

        # ======================= DIGITIZER INIT ==============================
        self.dgtBox = wx.StaticBox(panel, label = "Digitizer", pos = (325, 5),
            size = (300, 230), style = wx.ALIGN_CENTER)
        wx.StaticText(self.dgtBox, label = "Device ID",
            style = wx.ALIGN_LEFT, size = (280, -1), pos = (10, 70))
        self.dgtDevice = wx.SpinCtrl(self.dgtBox, size = (134, -1),
            pos = (10, 95))
        self.dgtConnect = wx.Button(self.dgtBox, pos = (154, 95),
            size = (134, -1))

        self.dgtProgram = wx.Button(self.dgtBox, pos = (10, 140), size = (278, -1),
            label = "Setup")
        self.dgtProgram.Bind(wx.EVT_BUTTON, self.programDgt)

        self.dgtStatus = wx.StaticText(self.dgtBox, style = wx.ALIGN_LEFT,
            size = (280, -1), pos = (10, 185))

        # ======================== ACQUISITION INIT ===========================
        self.acqBox = wx.StaticBox(panel, label = "Acquisition", pos = (10, 240),
            size = (615, 261), style = wx.ALIGN_CENTER)

        self.acqGlbNumEnable = wx.CheckBox(self.acqBox, size = (134, -1), pos = (10, 4))
        self.acqGlbNumEnable.Bind(wx.EVT_CHECKBOX, self.updateGlobalNum)
        wx.StaticText(self.acqBox, label = "Global events", style = wx.ALIGN_LEFT,
            size = (134, -1), pos = (33, 5))
        wx.StaticText(self.acqBox, label = "Trigger bias (V)", style = wx.ALIGN_LEFT,
            size = (134, -1), pos = (154, 5))
        self.acqGlbNum = wx.SpinCtrl(self.acqBox, max = 9E4, size = (134, -1),
            pos = (10, 30))
        self.acqTrgBias = wx.SpinCtrl(self.acqBox, max = 1000, size = (134, -1),
            pos = (154, 30))

        self.acqNumPanel = wx.Panel(self.acqBox, pos = (0, 70), size = (154, 144))
        wx.StaticText(self.acqNumPanel, label = "Events", style = wx.ALIGN_LEFT,
            size = (134, -1), pos = (10, 0))
        self.acqNum = wx.SpinCtrl(self.acqNumPanel, max = 9E4, size = (134, -1),
            pos = (10, 25))
        wx.StaticText(self.acqBox, label = "Sensor bias (V)", style = wx.ALIGN_LEFT,
            size = (134, -1), pos = (154, 70))
        self.acqSensBias = wx.SpinCtrl(self.acqBox, max = 1000, size = (134, -1),
            pos = (154, 95))

        self.acqAdd = wx.Button(self.acqBox, pos = (10, 140), size = (134, -1),
            label = "Add")
        self.acqAdd.Bind(wx.EVT_BUTTON, self.addToList)
        self.acqDel = wx.Button(self.acqBox, pos = (154, 140), size = (134, -1),
            label = "Remove")
        self.acqDel.Bind(wx.EVT_BUTTON, self.deleteFromList)

        wx.StaticLine(self.acqBox, pos = (10, 185), size = (280, 1))

        self.acqStart = wx.Button(self.acqBox, pos = (10, 196), size = (134, -1),
            label = "Run")
        self.acqStart.Bind(wx.EVT_BUTTON, self.startAcquisition)
        self.acqStart.Disable()
        self.acqStart.SetBackgroundColour((41, 114, 51, 255))

        self.acqStop = wx.Button(self.acqBox, pos = (154, 196), size = (134, -1),
            label = "Stop")
        self.acqStop.Disable()
        self.acqStop.SetBackgroundColour((114, 41, 41, 255))

        self.acqSetup = wx.ListCtrl(self.acqBox, pos = (325, 5),
            style = wx.LC_REPORT ^ wx.LC_SINGLE_SEL, size = (278, 225))

        COLUMNS = ["Run", "Events", "Sensor bias (V)"]
        for col in COLUMNS:
            self.acqSetup.AppendColumn(col)

        self.acqSetup.Bind(wx.EVT_LIST_ITEM_SELECTED, self.updateFromList)

        self.optMan = wx.Button(panel, pos = (10, 510), size = (200, -1),
            label = "Manual control")
        self.optMan.Disable()
        self.optExit = wx.Button(panel, pos = (575, 510), size = (50, -1),
            label = "Quit")
        self.optExit.Bind(wx.EVT_BUTTON, self.close)

        # ============================ CONFIG INIT ============================
        self.populateHvPorts()
        self.populateFromConfig()
        self.resetHv()

        self.Show()
        self.Center()

    # =========================== CONFIG INIT =================================

    def populateHvPorts(self, event = None):
        self.hvPort.Clear()
        hvPorts = backend.hvGetResources()
        length = len(hvPorts)
        if length > 0:
            self.hvPort.Append(hvPorts)
            self.hvPort.SetValue(hvPorts[0])

        self.hvDevPanel.Enable(length > 0)

    def populateFromConfig(self):
        config = backend.CONFIG
        keys = config.keys()

        getIfConfigured("DIGITIZER_ID", self.dgtDevice)

        numKey = "MAX_EVENTS"
        numInKeys = numKey in keys
        if numInKeys:
            num = config[numKey]
            self.acqGlbNum.SetValue(num)
            self.acqGlbNumEnable.SetValue(True)

            sensBiasKey = "SENSOR_BIAS"
            sensBiasInKey = sensBiasKey in keys
            if sensBiasInKey:
                self.acqSetup.DeleteAllItems()
                for i, bias in enumerate(config[sensBiasKey]):
                    self.acqSetup.Append([i, num, bias])

                self.acqSetup.Focus(0)
                self.updateFromList()

            self.acqDel.Enable(sensBiasInKey)
        else:
            self.acqGlbNumEnable.SetValue(False)

        self.acqNumPanel.Enable(not numInKeys)
        self.acqGlbNum.Enable(numInKeys)
        self.updateGlobalNum()

        getIfConfigured("HIGHVOLTAGE_ID", self.hvDevice)
        getIfConfigured("TRIGGER_BIAS", self.acqTrgBias)

    # ============================= RUN LIST ==================================

    def deleteFromList(self, event):
        target = self.acqSetup.GetFocusedItem()
        self.acqSetup.DeleteItem(target)

        self.updateListRun()

    def addToList(self, event):
        target = self.acqSetup.GetFocusedItem()
        index = target if target != -1 else 0
        self.acqSetup.InsertItem(index, "")
        if self.acqGlbNumEnable.IsChecked():
            num = self.acqGlbNum.GetValue()
        else:
            num = self.acqNum.GetValue()
        self.acqSetup.SetItem(index, 1, str(num))
        self.acqSetup.SetItem(index, 2,
            str(self.acqSensBias.GetValue()))

        self.updateListRun(index)

    def updateListRun(self, nextFocus = None):
        count = self.acqSetup.GetItemCount()
        for i in range(count):
            self.acqSetup.SetItem(i, 0, str(i))

        if count != 0:
            if nextFocus != None:
                self.acqSetup.Focus(nextFocus)
            self.updateFromList()

        self.acqDel.Enable(count > 0)

    def updateFromList(self, event = None):
        item = self.acqSetup.GetFocusedItem()

        self.acqNum.SetValue(
            self.acqSetup.GetItem(item, 1).GetText())
        self.acqSensBias.SetValue(
            self.acqSetup.GetItem(item, 2).GetText())

    def updateGlobalNum(self, event = None):
        checked = self.acqGlbNumEnable.IsChecked()
        self.acqNumPanel.Enable(not checked)
        self.acqGlbNum.Enable(checked)

        GLOBAL_COL_WIDTH = [140, 0, 140]
        LOCAL_COL_WIDTH = [80, 80, 120]

        widths = GLOBAL_COL_WIDTH if checked else LOCAL_COL_WIDTH
        for i, width in enumerate(widths):
            self.acqSetup.SetColumnWidth(i, width)

    # ========================== INTERACTION WITH HIGH VOLTAGE ================

    def connectHv(self, event):

        attempt = 0
        maxAttempts = 5

        hvPort = self.hvPort.GetStringSelection()
        hvDevice = self.hvDevice.GetValue()
        while attempt <= maxAttempts:
            status = "connecting... (attempt {} of {})".format(attempt,
                maxAttempts)
            self.setHvStatus(status)
            if backend.connectHighVoltage(hvPort, hvDevice):
                hv = backend.getHighVoltage()
                if not hv.getSupported():
                    self.setHvStatus("fail, board not supported.")
                    return
                while not hv.getRemote():
                    text = "{} is configured in LOCAL control mode. Please set connection to REMOTE to continue...".format(
                        backend.getHighVoltage().getModel())
                    if not self.hvFailModal.ShowInCenter(text):
                        self.resetHv()
                        return

                self.setHvStatus("connected to {}.".format(hv.getModel()))
                self.setDgtStatus("disconnected.")
                self.hvConnect.SetLabel("Disconnect")
                self.hvConnect.Bind(wx.EVT_BUTTON, self.resetHv)
                self.dgtBox.Enable()
                self.hvProgram.Enable()
                return
            else:
                attempt += 1

        self.setHvStatus("failed to connect.")

    def resetHv(self, event = None):
        self.resetDgt()
        backend.disconnectHighVoltage()

        self.hvConnect.SetLabel("Connect")
        self.hvConnect.Bind(wx.EVT_BUTTON, self.connectHv)
        self.dgtBox.Disable()
        self.hvProgram.Disable()
        self.setHvStatus("disconnected.")
        self.setDgtStatus("waiting for high voltage.")

    def setHvStatus(self, status):
        self.hvStatus.SetLabel("Status: " + status)

    def programHv(self, event = None):
        while self.hvProgramModal.ShowInCenter():
            sensChn = self.hvProgramModal.hvSensChn
            trgChn = self.hvProgramModal.hvTrgChn

            if sensChn.GetValue() == trgChn.GetValue():
                text = "Cannot use the same channel for both devices. Please input two different channel numbers."
                if self.hvFailModal.ShowInCenter(text):
                    continue
                break

            saveToConfig("SENSOR_CHANNEL", sensChn)
            saveToConfig("TRIGGER_CHANNEL", trgChn)
            return

    # ===================== INTERACTION WITH DIGITIZER ========================

    def connectDgt(self, event):


        attempt = 0
        maxAttempts = 5

        dgtPort = 0
        dgtDevice = self.dgtDevice.GetValue()
        while attempt <= maxAttempts:
            status = "connecting... (attempt {} of {})".format(attempt,
                maxAttempts)
            self.setDgtStatus(status)
            if backend.connectDigitizer(dgtPort, dgtDevice):
                dgt = backend.getDigitizer()
                dgt.allocateEvent()
                dgt.mallocBuffer()
                self.setDgtStatus("connected to {}.".format(dgt.getModel()))
                self.dgtConnect.SetLabel("Disconnect")
                self.dgtConnect.Bind(wx.EVT_BUTTON, self.resetDgt)
                self.dgtProgram.Enable()
                return
            else:
                attempt += 1

        self.setDgtStatus("failed to connect.")

    def resetDgt(self, event = None):
        backend.disconnectDigitizer()
        self.dgtProgram.Disable()
        self.dgtConnect.Bind(wx.EVT_BUTTON, self.connectDgt)
        self.dgtConnect.SetLabel("Connect")
        self.setDgtStatus("disconnected.")

    def setDgtStatus(self, status):
        self.dgtStatus.SetLabel("Status: " + status)

    def programDgt(self, event):
        modal = self.dgtProgramModal
        if modal.ShowInCenter():
            offsets = []
            for i, o in enumerate(modal.dgtChnOffsetModal.dgtChnOffsets):
                offsets.append(o.GetValue())
            backend.CONFIG["CHANNEL_OFFSET"] = offsets

            global SAMPLING_FREQUENCIES
            saveToConfig("SAMPLING_FREQUENCY", modal.dgtFreq,
                SAMPLING_FREQUENCIES[0])
            saveToConfig("BLT_EVENTS_MAX", modal.dgtBLTEvts)
            global EVENT_SAMPLES
            saveToConfig("SAMPLES_PER_EVENT", modal.dgtEvtSamples,
                EVENT_SAMPLES[0])
            saveToConfig("POST_TRIGGER_DELAY", modal.dgtTrgDelay)
            global ENABLED_CHANNELS
            saveToConfig("ENABLED_GROUPS", modal.dgtEnChns,
                ENABLED_CHANNELS[0])
            saveToConfig("TRIGGER_BASELINE", modal.dgtTrgOfst)
            saveToConfig("TRIGGER_THRESHOLD", modal.dgtTrgThresh)
            saveToConfig("USE_INTERNAL_CORRECTION", modal.dgtDataCorr)

    # ============================= ACQUISITION ===============================

    def startAcquisition(self, event):
        backend.programDigitizer()

    def close(self, event):
        self.resetHv()
        self.Close(True)

if __name__ == "__main__":
    print("I'm a module, please don't run me alone.")
    exit()
