def closed_multiple(n, x):
    n = n + x / 2
    n = n - (n % x)
    return int(n)
