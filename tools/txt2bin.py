def init():
    name = "../../../wafer2-100-200-shifted/400V_x100y510"

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

    with open(name + ".bin", "wb") as file:
        for event in events:
            for channel in event:
                for sample in channel:
                    file.write((sample).to_bytes(2, byteorder = "big", signed = False))

    with open(name + ".bin", "rb") as file:
        contents = file.read()
        while


if __name__ == "__main__":
    init()
