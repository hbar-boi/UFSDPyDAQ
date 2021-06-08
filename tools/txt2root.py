import ROOT as rt
import os
from array import array
from multiprocessing import Pool

class TreeFile():

    def __init__(self, path, name):
        path = os.path.join(path, "{}.root".format(name))

        self.file = rt.TFile(path, "RECREATE", name, 9)
        self.tree = rt.TTree("wfm", "Digitizer waveform")

        self.bias = array("I", [0])
        self.tree.Branch("bias", self.bias, "bias/I")

        self.frequency = array("I", [0])
        self.tree.Branch("freq", self.frequency, "freq/I")

        self.length = array("I", [0])
        self.tree.Branch("size", self.length, "size/I")

        self.pos = rt.std.vector("int")()
        self.tree.Branch("pos", self.pos)

        self.channels = []
        for c in range(16):
            wave = rt.std.vector("int")()
            self.tree.Branch("w{}".format(c), wave)
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
        self.bias[0] = 0

        self.pos.clear()

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

    def setPosition(self, x, y):
        self.pos.push_back(int(x))
        self.pos.push_back(int(y))

    def setBias(self, bias):
        self.bias[0] = int(bias)


def init():
    global orig
    global dest
    orig = "../../wafer2-100-200-txt/"
    dest = "../../wafer2-100-200-root/all"
    os.makedirs(dest, exist_ok = True)

    root = TreeFile(dest, "combined")
    n = 0
    for file in os.listdir(orig):
        n += convert(file, root)
    root.close()
    print(n)

def convert(name, root):
    global orig
    global dest
    events = []
    with open(os.path.join(orig, name), "r") as file:
        event = None
        for i, line in enumerate(file):
            if line[0] == "#":
                if i > 0:
                    events.append(event)
                event = [[] for k in range(18)]
            else:
                cols = line.strip("\n").split(",")
                for j, col in enumerate(cols):
                    event[j].append(int(col))
        events.append(event)

    for event in events:
        root.setFrequency(5E3)
        root.setEventLength(1024)

        bias = name[:-4].split("_")[0][:-1]
        root.setBias(bias)

        x = name[:-4].split("_")[1].split("y")[0][1:]
        y = name[:-4].split("_")[1].split("y")[1]
        root.setPosition(x, y)

        for i, channel in enumerate(event):
            group = int(i / 9)
            if i == 8 or i == 17:
                root.setTrigger(group, channel, 1024)
            else:
                root.setChannel(i - group, channel, 1024)
        root.fill()

    return len(events)

if __name__ == "__main__":
    init()
