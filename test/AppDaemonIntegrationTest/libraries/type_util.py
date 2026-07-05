from typing import Any


def extract_from_dictionary(dictionary: dict[Any, Any], key: Any) -> Any:
    result = None
    if key in dictionary:
        result = dictionary[key]
        del dictionary[key]
    return result
