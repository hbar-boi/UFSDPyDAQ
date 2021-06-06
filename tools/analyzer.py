import matplotlib.pyplot as plt
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

        earliests, minimums = [], []
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
            triggers[1]) for channel in self.channels[8:16]])

        self.means = np.array([self.coupleAC(
            self.average(channel)) for channel in self.channels])

        print(self.integrate(self.means[0:10]))

        end = time.time()
        print("Data ready, took another {} seconds".format(end - start))

    def parse(self, tree, params):
        vectors = {}
        for label in params:
            vector = rt.std.vector("double")()
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
    file = "../../../wafer2-100-200-root/wafer2-100-200/400V_x320y530.root"
    a = Analyzer(file)

    fig, plots = plt.subplots(12, sharex = True)
    x = np.arange(0, TIME_STEP * 1024, TIME_STEP)
    titles = ["CHN{}".format(i) for i in range(9)]

    for t, event in enumerate(a.means[0:9]):
        """peaks = sp.find_peaks([-x for x in channel], prominence = 12)
            for p in peaks[0]:
                plots[t].axvline(x = x[p])"""
        plots[t].set_ylabel(titles[t], fontsize = 10)
        plots[t].set_ylim((-220, 100))
        plots[t].plot(x, event, "-", linewidth = 1)

    plots[9].set_ylabel("TRG", fontsize = 10)
    plots[9].plot(x, a.trigger, "-", linewidth = 1)

    plots[10 + 1].set_xlabel("Time [ns]", fontsize = 10)

    plt.show()
