import numpy as np
import ROOT as rt
import matplotlib.pyplot as plt
import os
import csv
import math
from array import array
from sklearn.linear_model import LinearRegression
from sklearn.multioutput import MultiOutputRegressor
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from scipy.stats import norm

from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

def init():
    data = np.zeros((101, 101, 9))

    for chn in range(9):
        for i in ["", "-2"]:
            print("/media/work/Waveforms/run4/analysis/chn{}/heatmap{}.root".format(chn, i))
            file = rt.TFile.Open("/media/work/Waveforms/run4/analysis/chn{}/heatmap{}.root".format(chn, i), "READ")
            tree = file.Get("heat")

            map = array("d", [0.0])
            tree.SetBranchAddress("heat", map)

            pos = rt.std.vector("double")()
            tree.SetBranchAddress("pos", pos)

            for e in range(tree.GetEntries()):
                tree.GetEntry(e)

                x = int(pos[0] / 10)
                y = int(pos[1] / 10)
                data[x][y][chn] = map[0]

            file.Close()
        #heatmap(data.transpose((2, 0, 1))[chn])

    x = data.reshape((10201, 9))
    y = np.array([np.array([x, y]) for x in range(0, 1010, 10) for y in range(0, 1010, 10)])

    x_train, x_test, y_train, y_test = train_test_split(x, y, random_state=1, test_size=0.01)
    reg = MLPRegressor().fit(x_train, y_train)

# %%
    y_test_predicted = reg.predict(x_test)
    print("Test Score: "+ str(reg.score(x_test, y_test)))

    y_test_resolution = y_test - y_test_predicted
    print(y_test_resolution)

def heatmap(data):
    m = np.arange(0, 101)
    n = np.arange(0, 101)
    x, y = np.meshgrid(m, n)

    def out(d, q):
        return (data)[d, q]

    z = out(x, y)
    fig, ax = plt.subplots(1, figsize = (9, 7))
    ax.set_ylabel("um", fontsize = 10)
    ax.set_xlabel("um", fontsize = 10)
    mesh = ax.pcolormesh(x, y, z, shading = "auto", cmap = "Blues")
    fig.colorbar(mesh, ax = ax)
    plt.show()

if __name__ == "__main__":
    init()
