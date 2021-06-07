import ROOT as rt
from array import array

class TreeFile():

    def __init__(self, name):
        self.file = rt.TFile("{}.root".format(name), "RECREATE", name, 8)
        self.tree = rt.TTree("wfm", "Digitizer waveform")

        self.frequency = array("I", [0])
        self.tree.Branch("freq", self.frequency, "freq/I")

        self.length = array("I", [0])
        self.tree.Branch("size", self.length, "size/I")

        self.channels = []
        for c in range(16):
            wave = rt.std.vector("int")()
            self.tree.Branch("chn{}".format(c), wave)
            self.channels.append(wave)

        self.triggers = []
        for t in range(2):
            wave = rt.std.vector("int")()
            self.tree.Branch("trg{}".format(t), wave)
            self.triggers.append(wave)

    def fill(self):
        self.tree.Fill()
        self.clear()

    def clear(self):
        self.length[0] = 0
        self.frequency[0] = 0

        for c in self.channels:
            c.clear()

        for t in self.triggers:
            t.clear()

    def close(self):
        self.file.Write()
        self.file.Close()

    def setChannel(self, index, data, length):
        channel = self.channels[index]
        channel.clear()
        for w in range(length):
            channel.push_back(int(data[w]))

    def setTrigger(self, index, data, length):
        trigger = self.triggers[index]
        trigger.clear()
        for t in range(length):
            trigger.push_back(int(data[t]))

    def setFrequency(self, frequency):
        self.frequency[0] = int(frequency)

    def setEventLength(self, length):
        self.length[0] = int(length)

    def getSize(self):
        return self.size

    def getStart(self):
        return self.start
