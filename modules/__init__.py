if __name__ == "__main__":
    print("I'm a module, please don't run me alone.")
    exit()
else:
    __all__ = ["digitizer", "highvoltage", "stage", "tree", "gui"]
    print("Loading control modules... ", end = "")
