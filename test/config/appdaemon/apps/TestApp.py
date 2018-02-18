import appdaemon.appapi as appapi

import Blocker
from libraries import DateTimeUtil
from robot.libraries import DateTime

import traceback


class TestApp(appapi.AppDaemon):
    def initialize(self):
        self.register_endpoint(self.api_callback, 'TestApp')

    def __call(self, data):
        args = data.get('args', [])
        kwargs = data.get('kwargs', {})
        function = data['function']
        self.log(
            'Calling function: ' + function + ' ' + str(args) +
            ' ' + str(kwargs))
        result = getattr(self, function)(*args, **kwargs)
        self.log('Function returns: ' + function + ' = ' + str(result))
        return result

    def api_callback(self, data):
        try:
            result = self.__call(data)
            return result, 200
        except:
            exception_str = traceback.format_exc()
            self.log(exception_str, level='WARNING')
            return exception_str, 500

    def test(self, arg):
        self.log(str(type(self.time())))
        return arg

    def __block(self, kwargs):
        Blocker.block()

    def unblock_until(self, when):
        self.run_once(self.__block, DateTimeUtil.to_time(when))
        Blocker.unblock()

    def unblock_for(self, duration):
        self.run_in(
            self.__block,
            DateTime.convert_time(duration, result_format='number'))
        Blocker.unblock()

    def get_current_time(self):
        return self.datetime().timestamp()

    def schedule_call_at(self, when, data):
        self.run_once(self.__call, DateTimeUtil.to_time(when), **data)

    def schedule_call_in(self, delay, data):
        self.run_in(
            self.__call,
            DateTime.convert_time(delay, result_format='number'),
            **data)

    def is_blocked(self):
        return Blocker.is_blocked()
