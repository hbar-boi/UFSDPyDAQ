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

INPUT_PATH = "/home/work/Desktop/100-200.root"
#INPUT_PATH = "/media/work/Waveforms/run4/analysis/amplitudes/100-200.root"

FIRST_CHANNEL = 0
LAST_CHANNEL = 10

NUM_CHANNELS = LAST_CHANNEL - FIRST_CHANNEL

def train(x, y):
    print(y)
    x_train, x_test, y_train, y_test = train_test_split(x, y, random_state=1, test_size=0.3)
    reg = MLPRegressor(hidden_layer_sizes=(100), random_state=1, max_iter=500).fit(x_train, y_train)

    y_test_predicted = reg.predict(x_test)
    print("Test Score: "+ str(reg.score(x_test, y_test)))

    y_test_resolution = y_test - y_test_predicted
    print(y_test_resolution)

def init():
    file = rt.TFile.Open(INPUT_PATH, "READ")
    data = file.Get("data")

    # Input tree setup
    position = rt.std.vector("double")()
    data.SetBranchAddress("pos", position)

    amplitudes = []
    for chn in range(FIRST_CHANNEL, LAST_CHANNEL + 1):
        amplitudes.append(array("d", [0.0]))
        data.SetBranchAddress("amp{}".format(chn), amplitudes[chn])

    points = data.GetEntries()
    out = np.zeros((points, NUM_CHANNELS + 1))
    xy = np.zeros((points, 2))
    for point in range(points):
            data.GetEntry(point)
            out[point] = np.array([amplitude[0] for amplitude in amplitudes])
            xy[point] = np.array(position)

            if point % 100 == 0:
                print("Progress: {}/{}".format(point, points))

    data.ResetBranchAddresses()
    file.Close()

    out = np.nan_to_num(out)
    train(out, xy)

if __name__ == "__main__":
    init()
