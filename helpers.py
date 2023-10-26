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
