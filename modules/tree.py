import ROOT as rt

class TreeFile():

    def __init__(self, name, channelMask):
        self.file = rt.TFile("{}.root".format(name), "RECREATE", 8)
        self.tree = rt.TTree("wfm", "Digitizer waveform")

        self.time = rt.std.vector("double")()
        self.tree.Branch("time", self.time)

        self.channels = []
        self.size, self.start = 0, 0
        if channelMask == 0b11:
            self.size = 18
        elif channelMask == 0b01:
            self.size = 9
        elif channelMask == 0b10:
            self.size = 9
            self.start = 9

        size = (8 / 9) * self.size
        start = (8 / 9) * self.start
        for c in range(size):
            wave = rt.std.vector("double")()
            self.tree.Branch("chn{}".format(c + start), wave)
            self.channels.append(wave)

        self.triggers = []
        for t in range(size / 8):
            trigger = rt.std.vector("double")()
            self.tree.Branch("trg{}".format(t + (start / 8)), trigger)

    def fill(self):
        self.tree.Fill()
        clear()

    def clear(self):
        self.time.clear()

        for c in self.channels:
            c.clear()

        for t in self.triggers:
            t.clear()

    def close(self):
        self.tfile.Write()
        self.tfile.Close()

    def setTime(self, samples, frequency, abs = 0):
        interval = 1 / frequency
        self.time.clear()
        for t in range(samples):
            self.time.push_back(float((t * interval) + abs))

    def setChannel(self, index, data, length):
        channel = self.channels[index]
        channel.clear()
        for w in range(length):
            channel.push_back(float(data[w]))

    def setTrigger(self, index, data, length):
        trigger = self.triggers[index]
        trigger.clear()
        for t in range(length):
            trigger.push_back(float(data[t]))

    def getSize(self):
        return self.size

    def getStart(self):
        return self.start
