import statistics


def anglemean(l):
    normalized360 = [x % 360 for x in l]
    normalized180 = [x - 360 if x >= 180 else x for x in normalized360]
    mean360 = statistics.mean(normalized360)
    mean180 = statistics.mean(normalized180)
    variance180 = statistics.variance(normalized180, mean180)
    variance360 = statistics.variance(normalized360, mean360)
    if variance180 < variance360:
        if mean180 < 0:
            mean180 += 360
        return mean180
    else:
        return mean360
