import gc

from UE4Parse import DefaultFileProvider
from UE4Parse.Assets.Objects.FGuid import FGuid
from UE4Parse.Encryption import FAESKey
from UE4Parse.Versions import VersionContainer, EUEVersion


def closed_multiple(n, x):
    n = n + x / 2
    n = n - (n % x)
    return int(n)


def rotate_image(img, angle):  # https://stackoverflow.com/a/47248339
    import cv2
    import numpy as np

    size_reverse = np.array(img.shape[1::-1]) # swap x with y
    M = cv2.getRotationMatrix2D(tuple(size_reverse / 2.), angle, 1.)
    MM = np.absolute(M[:,:2])
    size_new = MM @ size_reverse
    M[:,-1] += (size_new - size_reverse) / 2.
    return cv2.warpAffine(img, M, tuple(size_new.astype(int)))


class FoxholeFileProvider(object):
    provider: DefaultFileProvider

    def __init__(self, pak_path):
        self.pak_path = pak_path

    def __enter__(self):
        gc.disable()
        self.provider = DefaultFileProvider(self.pak_path, VersionContainer(EUEVersion.GAME_UE4_24))
        self.provider.initialize()
        aeskeys = {
            FGuid(0, 0, 0, 0): FAESKey("0x0000000000000000000000000000000000000000000000000000000000000000"),
        }
        self.provider.submit_keys(aeskeys)
        gc.enable()
        return self.provider

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.provider.close()
