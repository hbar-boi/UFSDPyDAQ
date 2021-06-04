import matplotlib.pyplot as plt
import numpy as np

def init():
    name = "../../../wafer2-100-200-txt/means.txt"
    with open(name, "r") as f:
        dict = eval(f.read())
        xmax = 0
        ymax = 0
        for a in dict.items():
            pos = eval(a[0])
            xmax = max(xmax, pos[0])
            ymax = max(ymax, pos[1])
            channels = a[1]
            for i, channel in enumerate(channels):
                channels[i] = 0 if channel == None else abs(channel)

        arr = np.zeros((xmax + 1, ymax + 1), dtype = "float")

        for k in dict.items():
            pos = eval(k[0])
            x = pos[0]
            y = pos[1]
            for l in range(x-100, x-50):
                for s in range(y-50, y):
                    try:
                        for m in range(0, 9):
                            arr[l][s] += k[1][m]
                    except:
                        pass

        plt.imshow(arr, cmap = "hot", interpolation = "nearest")
        plt.show()


if __name__ == "__main__":
    init()
