import os


def getFile(filename, length=None):
    """return contents of the file with the given name"""
    filename = os.path.join(os.path.dirname(__file__), filename)
    with open(filename, "rb") as data_file:
        return data_file.read(length)
