import numpy as np

def init():
    name = "../../../wafer2-100-200-shifted/400V_x100y510"

    mat = np.loadtxt(name + ".txt", dtype = "float", delimiter = ",")

    np.savez_compressed(name + ".npz", mat)

if __name__ == "__main__":
    init()
