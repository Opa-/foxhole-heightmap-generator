def closed_multiple(n, x):
    n = n + x / 2
    n = n - (n % x)
    return int(n)


def rotate_image(image, angle):  # https://stackoverflow.com/a/9042907
    import cv2
    import numpy as np

    image_center = tuple(np.array(image.shape[1::-1]) / 2)
    rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
    result = cv2.warpAffine(image, rot_mat, image.shape[1::-1], flags=cv2.INTER_LINEAR)
    return result
