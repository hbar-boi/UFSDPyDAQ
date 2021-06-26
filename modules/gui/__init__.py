if __name__ == "__main__":
    print("I'm a module, please don't run me alone.")
    exit()
else:
    __all__ = ["main", "modals", "config"]
    print("[GUI ok] ", end = "")
