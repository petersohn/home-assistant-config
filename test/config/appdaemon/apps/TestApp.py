import appdaemon.appapi as appapi

import Blocker
from libraries import DateTimeUtil
from robot.libraries import DateTime

import traceback


class TestApp(appapi.AppDaemon):
    class PendingState():
        def __init__(self):
            self.state = None
            self.listener = None

        def __str__(self):
            return 'PendingState(' + str(self.state) + ')'

    def initialize(self):
        self.register_endpoint(self.api_callback, 'TestApp')
        self.__block_listeners = []
        self.__block_timers = []
        self.__pending_states = {}

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
        Blocker.main_blocker.block()
        for listener in self.__block_listeners:
            self.cancel_listen_state(listener)
        self.__block_listeners.clear()
        for timer in self.__block_timers:
            self.cancel_timer(timer)
        self.__block_timers.clear()

    def __block_on_state(self, entity, attribute, old, new, kwargs):
        Blocker.main_blocker.block()

    def unblock_until(self, when):
        self.__block_timers.append(
            self.run_once(self.__block, DateTimeUtil.to_time(when)))
        Blocker.main_blocker.unblock()

    def unblock_for(self, duration):
        self.__block_timers.append(
            self.run_in(
                self.__block,
                DateTime.convert_time(duration, result_format='number')))
        Blocker.main_blocker.unblock()

    def unblock_until_state_change(
            self, entity, timeout=None, deadline=None, **kwargs):
        self.__block_listeners.append(
            self.listen_state(
                self.__block_on_state, entity, oneshot=True, **kwargs))
        if timeout is not None:
            self.unblock_for(timeout)
        if deadline is not None:
            self.unblock_until(deadline)
        Blocker.main_blocker.unblock()

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
        return Blocker.main_blocker.is_blocked()

    def __state_set(self, entity, attribute, old, new, kwargs):
        self.log(
            'state changed: ' + entity + '='
            + str(new) + ' pending=' + str(self.__pending_states))
        pending_state = self.__pending_states.get(
            entity, self.PendingState())
        if pending_state.state != new:
            return
        self.cancel_listen_event(pending_state.listener)
        del self.__pending_states[entity]
        if len(self.__pending_states) == 0:
            Blocker.set_state_blocker.unblock()

    def __block_for_state_change(self, entity, state):
        old_state = self.get_state(entity)
        self.log(
            'state change initiated: old='
            + str(old_state) + ' state=' + str(state))
        if str(old_state) == str(state):
            return
        Blocker.set_state_blocker.block()
        pending_state = self.__pending_states.setdefault(
            entity, self.PendingState())
        pending_state.state = state
        if not pending_state.listener:
            pending_state.listener = self.listen_state(
                self.__state_set, entity)

    def set_sensor_state(self, entity, state):
        state = str(state)
        self.__block_for_state_change(entity, state)
        self.set_state(entity, state=state)

    def turn_on(self, entity):
        self.__block_for_state_change(entity, 'on')
        super(TestApp, self).turn_on(entity)

    def turn_off(self, entity):
        self.__block_for_state_change(entity, 'off')
        super(TestApp, self).turn_off(entity)
