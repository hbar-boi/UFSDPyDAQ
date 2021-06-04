import matplotlib.pyplot as plt
import numpy as np
import os
import scipy.signal as sp

plt.style.use("seaborn-whitegrid")

TIME_STEP = 0.2 # ns

CORRECTION_THRESH = 1700

class Analyzer():

    def __init__(self, file):
        head = file.split("_")[1][:-4]
        self.xpos = int(head.split("y")[0][1:])
        self.ypos = (head.split("y")[1])
        self.channels, self.triggers, self.extra = self.parse(file)

        self.channels = self._removeShotPeaks(self.channels)
        self.channels = self._applyTimeCorrection(self.channels)

        self.extra = self._applyTimeCorrection(self.extra)
        self.triggers = self._applyTimeCorrection(self.triggers)

        self.means = self._eventsMean(self.channels)
        self.means = self._dcCouple(self.means)

    def parse(self, name):
        events = []
        with open(name, "r") as file:
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

        channels, triggers, extra = [], [], []
        for event in events:
            channels.append(event[0:8] + event[9:10])
            triggers.append(event[8:9] + event[17:18])
            extra.append(event[10:12])

        return channels, triggers, extra

    def _applyTimeCorrection(self, data):
        for i, event in enumerate(data):
            delta = self._getIndexDelay(i)
            for j, channel in enumerate(event):
                mean = np.mean(channel[:-50])

                event[j] = channel[delta:]
                event[j] += ([mean] * delta)

        return data

    def _removeShotPeaks(self, data):
        for l, event in enumerate(data):
            for j, channel in enumerate(event[1:]):
                inverted = [-x for x in channel]
                shot = sp.find_peaks(inverted, prominence = 50, width = [1, 4])
                for i, peak in enumerate(shot[0]):
                    base = shot[1]["left_ips"][0]
                    for k in range(peak - 1, peak + 1):
                        channel[k] = channel[int(base)]
        return data

    def _getIndexDelay(self, target):
        def getFirstIndexAt(data, index):
            return next(
                x[0] for x in enumerate(data) if x[1] < index)

        if not hasattr(self, "minimum"):
            last = 1024
            for event in self.triggers:
                last = min(last,
                    getFirstIndexAt(event[0], CORRECTION_THRESH))
            self.minimum = last

        delta = getFirstIndexAt(self.triggers[target][0], CORRECTION_THRESH) - self.minimum
        return delta

    def _eventsMean(self, data):
        averages = np.zeros((9, 1024))
        devstds = np.zeros((9, 1024))
        for event in data:
            for j, channel in enumerate(event):
                for i, sample in enumerate(channel):
                    averages[j][i] += sample

        for i, a in enumerate(averages):
            for l, k in enumerate(a):
                averages[i][l] /= len(data)

        return averages

    def _dcCouple(self, data):
        for i, channel in enumerate(data):
            mean = np.mean(channel[:-100])
            for j, sample in enumerate(channel):
                data[i][j] -= mean

        return data

if __name__ == "__main__":
    name = "../../../wafer2-100-200-txt/"
    files = os.listdir(name + "wafer2-100-200-shifted")

    out = {}
    for i, file in enumerate(files[1:2]):
        analyzer = Analyzer(name + "wafer2-100-200-shifted/" + file)
        means = analyzer.means
        for a in means:
            print(max(a))
            print(np.trapz(a, dx = 2E-10))
