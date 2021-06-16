import scipy.signal as sp
import matplotlib.pyplot as plt
import numpy as np
from multiprocessing import Pool
from functools import partial
from array import array
import ROOT as rt
import time, os, gc

plt.style.use("seaborn-whitegrid")

TIME_STEP = 0.2 # ns
RECORD_LENGTH = 1024

TRIGGER_PROMINENCE = 700

CACHE_FILE = "cache.npz"
PROCESSORS = 8

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
                self.triggers = data["triggers"]

        if not cache or make:
            if os.path.exists(CACHE_FILE):
                os.remove(CACHE_FILE)

            params = {
                "channels": [(path, "w{}".format(i), i) for i in range(16)],
                "triggers": [(path, "trg{}".format(i), i) for i in range(2)],
                "extras": [(path, i, i) for i in ["pos", "bias", "freq", "size"]]}

            params["channels"].reverse()

            with Pool(PROCESSORS) as pool:
                channels = pool.starmap(Analyzer.parse, params["channels"])
                triggers = pool.starmap(Analyzer.parse, params["triggers"])

            def reorder(data):
                out = np.empty(len(data), dtype = object)
                for pair in data:
                    out[pair[0]] = pair[1]

                return out

            self.channels = reorder(channels)
            self.triggers = reorder(triggers)

        if make:
            np.savez(CACHE_FILE,
                channels = self.channels, triggers = self.triggers)

        end = time.time()
        print("Parsing rootfile took {} seconds".format(end - start))
        print("Applying corrections to data...")
        start = time.time()

        self.process()

        end = time.time()
        print("Data ready, took another {} seconds".format(end - start))


    def process(self):
        """self.channels = np.array(
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
        for trigger in self.triggers:
            index, begin = getEarliest(trigger)
            earliests.append(index)
            minimums.append(begin)

        winner = minimums.index(min(minimums))
        self.trigger = self.triggers[winner][earliests[winner]]
        self.minimum = minimums[winner]

        self.channels[0:8] = np.array([self.applyTimeCorrection(channel,
            self.triggers[0]) for channel in self.channels[0:8]])
        self.channels[8:16] = np.array([self.applyTimeCorrection(channel,
            self.triggers[1]) for channel in self.channels[8:16]])

        self.means = np.array([self.coupleAC(
            self.average(channel)) for channel in self.channels])

        print(self.integrate(self.means[0:10]))"""

    def parse(path, param, index):
        file = rt.TFile.Open(path, "READ")
        tree = file.Get("wfm")

        vector = rt.std.vector("double")()
        tree.SetBranchAddress(param, vector)

        events = 100
        out = np.empty((events, RECORD_LENGTH))
        for e in range(events):
            tree.GetEntry(e)
            out[e] = np.array(vector)

        tree.ResetBranchAddresses()
        return (index, out)

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
            peaks = sp.find_peaks(-samples, prominence = 30, width = [1, 4])
            for i, peak in enumerate(peaks[0]):
                half = int(np.ceil(peaks[1]["widths"][i] / 2))
                start = peak - half
                end = peak + half

                base = np.mean((samples[start], samples[end]))
                for i in range(start, end):
                    samples[i] = base
            return samples

        return np.array([correct(s) for s in data])

    def average(self, data):
        out = [np.mean(i) for i in data.transpose()]
        return np.array(out)

    def coupleAC(self, data):
        mean = np.mean(data[:-100])
        return np.array([sample - mean for sample in data])

    def integrate(self, data):
        return np.array([np.trapz(samples) for samples in data])

if __name__ == "__main__":

    file = "/home/work/Github/data/griglia20um.root"
    res = Analyzer(file, False)

    fig, plots = plt.subplots(12, sharex = True)
    x = np.arange(0, TIME_STEP * 1024, TIME_STEP)
    titles = ["CHN{}".format(i) for i in range(9)]

    for t, channel in enumerate(res.channels[0:9]):
        for event in (channel):

            plots[t].set_ylabel(titles[t], fontsize = 10)
            plots[t].plot(x, event, "-", linewidth = 1)

    """for e, event in enumerate(res.means[0:9]):
        peaks = sp.find_peaks(-event, prominence = 6)[0]
        for p in peaks:
            plots[e].axvline(x = x[p])

        if len(peaks) > 0:
            height = event[peaks[0]]
            plots[e].set_ylim([height * 1.1 , -height / 2])
        else:
            plots[e].set_ylim([250, -150])

        plots[e].set_ylabel(titles[e], fontsize = 10)
        plots[e].plot(x, event, "-", linewidth = 1)"""

    plots[9].plot(x, res.trigger, linewidth = 1)
    plots[9].set_ylabel("TRG", fontsize = 10)

    plots[10].plot(x, res.means[9], linewidth = 1)
    plots[10].set_ylabel("DC", fontsize = 10)

    plots[11].plot(x, res.means[10], linewidth = 1)
    plots[11].set_ylabel("VREF", fontsize = 10)
    plots[11].set_xlabel("Time [ns]", fontsize = 10)"""

    plt.show()
