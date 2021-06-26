import matplotlib.pyplot as plt
import numpy as np
import ROOT as rt
from array import array


def init():
    channels = np.zeros((1010, 1010))
    for i in [0, 2]:
        channels += channel(i)

    def out(d, q):
        return (channels)[d, q]

    m = np.arange(0, 1010, 10)
    n = np.arange(0, 1010, 10)
    x, y = np.meshgrid(m, n)

    z = out(x, y)
    fig, ax = plt.subplots(1, figsize = (7, 7))
    ax.set_ylabel("um", fontsize = 10)
    ax.set_xlabel("um", fontsize = 10)
    ax.pcolormesh(x, y, z, shading = "auto", cmap = "Blues")
    plt.show()

def channel(id):
    out = np.zeros((1010, 1010))

    for i in ["", "-2"]:
        file = rt.TFile.Open("/media/work/Waveforms/run4/analysis/chn{}/heatmap{}.root".format(id, i), "READ")
        tree = file.Get("heat")

        map = array("d", [0.0])
        tree.SetBranchAddress("heat", map)

        pos = rt.std.vector("double")()
        tree.SetBranchAddress("pos", pos)

        for e in range(tree.GetEntries()):
            tree.GetEntry(e)

            x = int(pos[0])
            y = int(pos[1])
            out[x][y] = map[0]

        file.Close()

    return out

if __name__ == "__main__":
    init()
