import hass

import datetime
from itertools import zip_longest
import traceback
from robot.libraries import DateTime


class TestApp(hass.Hass):
    def initialize(self):
        self.log("********** INIT ***********")
        self.register_endpoint(self.api_callback, "TestApp")

    def __call(self, data):
        args = data.get("args", [])
        kwargs = data.get("kwargs", {})
        arg_types = data.get("arg_types") or []
        kwarg_types = data.get("kwarg_types") or {}
        result_type = data.get("result_type")

        def convert(target_type, value):
            if target_type is not None:
                wrapper = eval(
                    target_type,
                    {
                        "convert_date": self.__convert_date,
                        "convert_time": self.__convert_time,
                        "convert_timedelta": self.__convert_timedelta,
                        "Int": lambda val: int(float(val)),
                        "percent": lambda val: int(float(val) * 100.0),
                    },
                    {},
                )
                return wrapper(value)
            else:
                return value

        def try_to_convert(value):
            if result_type is not None:
                try:
                    return convert(result_type, value)
                except TypeError:
                    pass
            return value

        def convert_output(value):
            if isinstance(value, str):
                return try_to_convert(value)
            if isinstance(value, dict):
                return {
                    convert_output(k): convert_output(v)
                    for k, v in value.items()
                }

            try:
                i = (convert_output(v) for v in value)
            except TypeError:
                pass
            else:
                return list(i)

            if isinstance(value, datetime.datetime):
                return DateTime.convert_date(value, result_format="timestamp")
            if isinstance(value, datetime.timedelta):
                return DateTime.convert_time(value, result_format="timer")

            return try_to_convert(value)

        function = data["function"]
        do_log = function != "log"
        if do_log:
            self.log(
                "Calling function: "
                + function
                + " "
                + str(args)
                + " "
                + str(kwargs)
            )

        if arg_types:
            args = [convert(t, v) for t, v in zip_longest(arg_types, args)]
        for name, kwarg_type in kwarg_types.items():
            kwargs[name] = convert(kwarg_type, kwargs[name])
        result = getattr(self, function)(*args, **kwargs)

        if do_log:
            self.log("Function returns: " + function + " = " + str(result))
        return convert_output(result)

    def api_callback(self, data):
        try:
            result = self.__call(data)
            return result, 200
        except:
            exception_str = traceback.format_exc()
            self.log(exception_str, level="ERROR")
            return exception_str, 500

    def test(self, arg):
        return arg

    def call_on_app(self, app, function, *args, **kwargs):
        return getattr(self.get_app(app), function)(*args, **kwargs)

    def is_all_apps_loaded(self, apps):
        return all(self.get_app(app) is not None for app in apps)

    def is_all_apps_unloaded(self, apps):
        return all(self.get_app(app) is None for app in apps)
