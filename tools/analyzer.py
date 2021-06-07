import matplotlib.pyplot as plt
import numpy as np
import os
import scipy.signal as sp

plt.style.use("seaborn-whitegrid")

TIME_STEP = 0.2 # ns

CORRECTION_THRESH = 1700

class Analyzer():

    def __init__(self, file, plots):
        self.pos = file.split("_")[1][:-4]
        self.plots = plots
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


    def show(self, j):
        plots = self.plots
        x = np.arange(0, TIME_STEP * 1024, TIME_STEP)
        titles = ["CHN{}".format(i) for i in range(9)]
        xpos = 800 - int(self.pos.split("y")[0][1:])
        ypos = int(self.pos.split("y")[1])
        plots[0][j].set_title("Laser spot @ ({}, {}) um".format(xpos, ypos), fontsize = 16)
        for t, channel in enumerate(self.means):
            peaks = sp.find_peaks([-x for x in channel], prominence = 12)
            for p in peaks[0]:

                plots[t][j].axvline(x = x[p])

            plots[t][0].set_ylabel(titles[t], fontsize = 10)
            plots[t][j].plot(x, channel, "-", linewidth = 1)
            plots[t][j].set_xlim([30, 50])
            plots[t][j].set_ylim([-220, 110])

        for i, event in enumerate(self.triggers[0:1]):
            for t, trigger in enumerate(event[0:1]):
                plots[9][0].set_ylabel("TRG", fontsize = 10)
                plots[9][j].set_xlim([30, 50])
                plots[9][j].plot(x, trigger, "-", linewidth = 1)

        extratitles = ["DC", "VREF"]
        for i, event in enumerate(self.extra[0:1]):
            for t, extra in enumerate(event):
                plots[10 + t][0].set_ylabel(extratitles[t], fontsize = 10)
                plots[10 + t][j].set_xlim([30, 50])
                plots[10 + t][j].plot(x, extra, "-", linewidth = 1)

        plots[10 + 1][j].set_xlabel("Time [ns]", fontsize = 10)

if __name__ == "__main__":
    name = "../../../wafer2-100-200-txt/wafer2-100-200-shifted"
    files = os.listdir(name)[30:34]

    fig, plots = plt.subplots(12, 4, sharex = True)
    for i, file in enumerate(files):
        analyzer = Analyzer(name + "/" + file, plots)
        analyzer.show(i)
=======
import scipy.signal as sp
import numpy as np
import ROOT as rt
import time, os, gc

plt.style.use('seaborn-whitegrid')

TIME_STEP = 0.2 # ns
RECORD_LENGTH = 1024

TRIGGER_PROMINENCE = 700

CACHE_FILE = "cache.npz"

class Analyzer():

    def __init__(self, path, cache = True):
        start = time.time()

        make = False
        if cache:
            data = None
            try:
                data = np.load(CACHE_FILE, allow_pickle = True)
            except:
                print("No cache found, creating it...")
                make = True
            else:
                print("Cached data found!")
                self.channels = data["channels"]
                triggers = data["triggers"]

        if not cache or make:
            if os.path.exists(CACHE_FILE):
                os.remove(CACHE_FILE)

            file = rt.TFile.Open(path, "READ")
            tree = file.Get("wfm")
            tree.Print()

            params = {"channels": ["chn{}".format(i) for i in range(16)],
                "triggers": ["trg{}".format(i) for i in range(2)]}

            self.channels = self.parse(tree, params["channels"])
            triggers = self.parse(tree, params["triggers"])

        if make:
            np.savez(CACHE_FILE,
                channels = self.channels, triggers = triggers)

        end = time.time()
        print("Parsing rootfile took {} seconds".format(end - start))
        print("Applying corrections to data...")
        start = time.time()

        self.channels = np.array(
            [self.removeShotPeaks(channel) for channel in self.channels])

        def getEarliest(data):
            current = 0
            minimum = RECORD_LENGTH
            for i, samples in enumerate(data):
                peak = sp.find_peaks(-samples,
                    prominence = TRIGGER_PROMINENCE)[0][0]
                if minimum >= peak:
                    minimum = peak
                    current = i

            return current, minimum

        """earliests, minimums = [], []
        for trigger in triggers:
            index, begin = getEarliest(trigger)
            earliests.append(index)
            minimums.append(begin)

        winner = minimums.index(min(minimums))
        self.trigger = triggers[winner][earliests[winner]]
        self.minimum = minimums[winner]

        self.channels[0:8] = np.array([self.applyTimeCorrection(channel,
            triggers[0]) for channel in self.channels[0:8]])
        self.channels[8:16] = np.array([self.applyTimeCorrection(channel,
            triggers[1]) for channel in self.channels[8:16]])"""

        self.means = np.array([self.coupleAC(
            self.average(channel)) for channel in self.channels])

        print(self.integrate(self.means[0:10]))

        end = time.time()
        print("Data ready, took another {} seconds".format(end - start))

    def parse(self, tree, params):
        vectors = {}
        for label in params:
            vector = rt.std.vector("int")()
            tree.SetBranchAddress(label, vector)
            vectors[label] = vector

        events = tree.GetEntries()
        out = np.empty((events, len(params), RECORD_LENGTH))
        for e in range(events):
            tree.GetEntry(e)
            out[e] = [np.array(vectors[label]) for label in params]

        tree.ResetBranchAddresses()
        return out.transpose(1, 0, 2)

    def applyTimeCorrection(self, data, trigger):

        def correct(samples, trigger):
            triggerPeak = sp.find_peaks(-trigger,
                prominence = TRIGGER_PROMINENCE)[0][0]
            delta = triggerPeak - self.minimum
            mean = np.mean(samples[:-100])

            result = np.concatenate((samples[delta:], np.full(delta, mean)))
            return result

        return np.array([correct(samples,
            trigger[i]) for i, samples in enumerate(data)])

    def removeShotPeaks(self, data):

        def correct(samples):
            peaks = sp.find_peaks(-samples, prominence = 50, width = [1, 4])
            for i, peak in enumerate(peaks[0]):
                start = int(peaks[1]["left_ips"][i])
                end = int(peaks[1]["right_ips"][i])

                base = np.mean((samples[start], samples[end]))
                for sample in range(start, end):
                    samples[sample] = base

            return samples

        return np.array([correct(samples) for samples in data])

    def average(self, data):
        out = [np.mean(i) for i in data.transpose()]
        return np.array(out)

    def coupleAC(self, data):
        mean = np.mean(data[:-100])
        return np.array([sample - mean for sample in data])

    def integrate(self, data):
        return np.array([np.trapz(samples) for samples in data])

if __name__ == "__main__":
    file = "../70.root"
    a = Analyzer(file, False)

    fig, plots = plt.subplots(12, sharex = True)
    x = np.arange(0, TIME_STEP * 1024, TIME_STEP)
    titles = ["CHN{}".format(i) for i in range(9)]

    for t, event in enumerate(a.channels[0:9]):
        """peaks = sp.find_peaks([-x for x in channel], prominence = 12)
            for p in peaks[0]:
                plots[t].axvline(x = x[p])"""
        plots[t].set_ylabel(titles[t], fontsize = 10)
        plots[t].plot(x, event[0], "-", linewidth = 1)

    plots[9].set_ylabel("TRG", fontsize = 10)

    plots[10 + 1].set_xlabel("Time [ns]", fontsize = 10)

>>>>>>> 298211bdc29cdf0bd7e2907448ef96058ba92b29
    plt.show()
