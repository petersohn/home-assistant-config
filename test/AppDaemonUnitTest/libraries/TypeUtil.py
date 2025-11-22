from typing import Any


def extract_from_dictionary(dictionary: Any, key: Any) -> Any:
    result = None
    if key in dictionary:
        result = dictionary[key]
        del dictionary[key]

    print(dictionary)

    return result


def repeat_item[T](item: T, count: int) -> list[T]:
    return [item] * count
