import ROOT as rt
import os

class TreeFile():

    def __init__(self, name, channelMask):
        self.file = rt.TFile("{}.root".format(name), "RECREATE", "", 9)
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

        size = int((8 / 9) * self.size)
        start = int((8 / 9) * self.start)
        for c in range(size):
            wave = rt.std.vector("double")()
            self.tree.Branch("chn{}".format(c + start), wave)
            self.channels.append(wave)

        self.triggers = []
        for t in range(int(size / 8)):
            trigger = rt.std.vector("double")()
            self.tree.Branch("trg{}".format(t + int((start / 8))), trigger)
            self.triggers.append(trigger)

    def fill(self):
        self.tree.Fill()
        self.clear()

    def clear(self):
        self.time.clear()

        for c in self.channels:
            c.clear()

        for t in self.triggers:
            t.clear()

    def close(self):
        self.file.Write()
        self.file.Close()

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

def init():
    orig = "../../../wafer2-100-200-txt/wafer2-100-200-shifted"
    dest = "../../../wafer2-100-200-root/wafer2-100-200-shifted"
    os.makedirs(dest, exist_ok = True)

    files = os.listdir(orig)[86:]
    for i, file in enumerate(files):
        print(file)
        print("{}/{}".format(i, len(files)))
        f = os.path.join(orig, file)
        d = os.path.join(dest, file[:-4])
        convert(f, d)

def convert(orig, dest):
    events = []
    with open(orig, "r") as file:
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

    root = TreeFile(dest, 0b11)
    for event in events:
        root.setTime(1024, 5E9)
        for i, channel in enumerate(event):
            group = int(i / 9)
            if i == 8 or i == 17:
                root.setTrigger(group, channel, 1024)
            else:
                root.setChannel(i - group, channel, 1024)
        root.fill()

    root.close()

if __name__ == "__main__":
    init()
