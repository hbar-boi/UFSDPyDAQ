import numpy as np
from multiprocessing import Pool
from array import array
import ROOT as rt

TIME_STEP = 0.2 # ns
RECORD_LENGTH = 1024

TRIGGER_PROMINENCE = 700

CACHE_FILE = "cache.npz"
PROCESSORS = 8
import ROOT as rt
from array import array
import os


class TreeFile():

    def __init__(self, path, name):
        path = os.path.join(path, "{}.root".format(name))

        self.file = rt.TFile(path, "RECREATE", name, 0)
        self.tree = rt.TTree("wfm", "Digitizer waveform")

        self.bias = array("d", [0.0])
        self.tree.Branch("bias", self.bias, "bias/D")

        self.frequency = array("d", [0.0])
        self.tree.Branch("freq", self.frequency, "freq/D")

        self.length = array("d", [0.0])
        self.tree.Branch("size", self.length, "size/D")

        self.pos = rt.std.vector("double")()
        self.tree.Branch("pos", self.pos)

        self.channels = []
        for c in range(16):
            wave = rt.std.vector("double")()
            self.tree.Branch("w{}".format(c), wave)
            self.channels.append(wave)

        self.triggers = []
        for t in range(2):
            wave = rt.std.vector("double")()
            self.tree.Branch("trg{}".format(t), wave)
            self.triggers.append(wave)

    def fill(self):
        self.tree.Fill()
        self.clear()

    def clear(self):
        self.length[0] = 0.0
        self.frequency[0] = 0.0
        self.bias[0] = 0.0

        self.pos.clear()

        for c in self.channels:
            c.clear()

        for t in self.triggers:
            t.clear()

    def write(self):
        self.file.Write()

    def close(self):
        self.file.Write()
        self.file.Close()

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

    def setFrequency(self, frequency):
        self.frequency[0] = float(frequency)

    def setEventLength(self, length):
        self.length[0] = float(length)

    def setPosition(self, x, y):
        self.pos.push_back(float(x))
        self.pos.push_back(float(y))

    def setBias(self, bias):
        self.bias[0] = float(bias)

def parse(i):
    file = rt.TFile.Open("/home/work/Github/data/griglia20umbis.root", "READ")
    tree = file.Get("wfm")

    out = TreeFile("/media/work/Waveforms/data", "file" + str(i))

    tot = tree.GetEntries()

    if (i + int(tot / PROCESSORS)) > tot:
        end = tot - i
    else:
        end = i + int(tot / PROCESSORS)
    for e in range(i, end, 1):
        channels = []
        for j in range(16):
            vector = rt.std.vector("double")()
            tree.SetBranchAddress("w{}".format(j), vector)
            channels.append(vector)

        triggers = []
        for j in range(2):
            vector = rt.std.vector("double")()
            tree.SetBranchAddress("trg{}".format(j), vector)
            triggers.append(vector)

        pos = rt.std.vector("double")()
        tree.SetBranchAddress("pos", pos)
        bias = array("d", [0.0])
        tree.SetBranchAddress("bias", bias)
        freq = array("d", [0.0])
        tree.SetBranchAddress("freq", freq)
        size = array("d", [0.0])
        tree.SetBranchAddress("size", size)

        tree.GetEntry(e)

        for j, c in enumerate(channels):
            out.setChannel(j, c, 1024)

        for j, t in enumerate(triggers):
            out.setTrigger(j, t, 1024)

        out.setBias(bias[0])
        out.setPosition(pos[0], pos[1])
        out.setFrequency(freq[0])
        out.setEventLength(size[0])

        out.fill()

        tree.ResetBranchAddresses()

        if i == 0 and e % (int(tot / 100)) == 0:
            print("Progress: {}%".format(int(100 * e / tot)))

    out.close()
    file.Close()

if __name__ == "__main__":
    file = rt.TFile.Open("/home/work/Github/data/griglia20umbis.root", "READ")
    tree = file.Get("wfm")

    tot = tree.GetEntries()
    r = range(0, tot, int(tot / PROCESSORS))
    with Pool(PROCESSORS) as pool:
        pool.map(parse, r)
