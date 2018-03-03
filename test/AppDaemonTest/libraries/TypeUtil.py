def extract_from_dictionary(dictionary, key):
    result = None
    if key in dictionary:
        result = dictionary[key]
        del dictionary[key]
    return result
