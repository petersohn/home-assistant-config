import appdaemon.appapi as appapi

import Blocker
from libraries import DateTimeUtil
from robot.libraries import DateTime

import traceback


class TestApp(appapi.AppDaemon):
    def initialize(self):
        self.register_endpoint(self.api_callback, 'TestApp')
        self.__block_listeners = []
        self.__block_timers = []

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
        return arg

    def __block(self, kwargs):
        Blocker.block()
        for listener in self.__block_listeners:
            self.cancel_listen_state(listener)
        self.__block_listeners.clear()
        for timer in self.__block_timers:
            self.cancel_timers(timer)
        self.__block_timers.clear()

    def __block_on_state(self, entity, attribute, old, new, kwargs):
        Blocker.block()

    def unblock_until(self, when):
        self.__block_timers.append(
            self.run_once(self.__block, DateTimeUtil.to_time(when)))
        Blocker.unblock()

    def unblock_for(self, duration):
        self.__block_timers.append(
            self.run_in(
                self.__block,
                DateTime.convert_time(duration, result_format='number')))
        Blocker.unblock()

    def unblock_until_state_change(
            self, entity, timeout=None, deadline=None, **kwargs):
        self.__block_listeners.append(
            self.listen_state(
                self.__block_on_state, entity, oneshot=True, **kwargs))
        if timeout is not None:
            self.unblock_for(timeout)
        if deadline is not None:
            self.unblock_until(deadline)
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
