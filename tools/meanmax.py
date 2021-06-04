import numpy as np

def init():
    name = "../../../wafer2-100-200-txt/wafer2-100-200-diag/400V_x170y230"

    events = []
    with open(name + ".txt", "r") as file:
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

    for event in events[1:2]:
        for j, channel in enumerate(event):
            raw = channel[:-50]
            mean = np.mean(raw)
            thresh = 2 * np.std(raw)
            for i, sample in enumerate(channel):
                if abs(sample - mean) >= thresh:
                    print("{} of {}".format(i, j))

if __name__ == "__main__":
    init()
