import appdaemon.plugins.hass.hassapi as hass

import Blocker
import mutex_graph
from libraries import DateTimeUtil
from robot.libraries import DateTime

import datetime
from itertools import zip_longest
import traceback


class TestApp(hass.Hass):
    class PendingState():
        def __init__(self):
            self.state = None
            self.listener = None

        def __str__(self):
            return 'PendingState(' + str(self.state) + ')'

    def initialize(self):
        self.register_endpoint(self.api_callback, 'TestApp')
        self.__block_listeners = {}
        self.__block_timers = []
        self.__pending_states = {}

    def __call(self, data):
        args = data.get('args', [])
        kwargs = data.get('kwargs', {})
        arg_types = data.get('arg_types') or []
        kwarg_types = data.get('kwarg_types') or {}
        result_type = data.get('result_type')

        def convert(target_type, value):
            if target_type is not None:
                wrapper = eval(target_type, {
                    'convert_date': self.__convert_date,
                    'convert_time': self.__convert_time,
                    'convert_timedelta': self.__convert_timedelta,
                    'Int': lambda val: int(float(val)),
                    'percent': lambda val: int(float(val) * 100.0)}, {})
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
                return {convert_output(k): convert_output(v)
                        for k, v in value.items()}

            try:
                i = (convert_output(v) for v in value)
            except TypeError:
                pass
            else:
                return list(i)

            if isinstance(value, datetime.datetime):
                return DateTime.convert_date(value, result_format='timestamp')
            if isinstance(value, datetime.timedelta):
                return DateTime.convert_time(value, result_format='timer')

            return try_to_convert(value)

        function = data['function']
        self.log(
            'Calling function: ' + function + ' ' + str(args) +
            ' ' + str(kwargs))

        if arg_types:
            args = [convert(t, v) for t, v in zip_longest(arg_types, args)]
        for name, kwarg_type in kwarg_types.items():
            kwargs[name] = convert(kwarg_type, kwargs[name])
        result = getattr(self, function)(*args, **kwargs)

        self.log('Function returns: ' + function + ' = ' + str(result))
        return convert_output(result)

    def api_callback(self, data):
        try:
            result = self.__call(data)
            return result, 200
        except:
            exception_str = traceback.format_exc()
            self.log(exception_str, level='ERROR')
            return exception_str, 500

    def test(self, arg):
        return arg

    def test_wrap(self, arg):
        return {'list': [arg, arg], 'tuple': (arg, arg)}

    def __convert_date(self, date):
        return DateTime.convert_date(date, result_format='datetime')

    def __convert_time(self, time):
        return DateTime.convert_time(time, result_format='number')

    def __convert_timedelta(self, time):
        return DateTime.convert_time(time, result_format='timedelta')

    def __block(self, kwargs):
        Blocker.main_blocker.block()
        for listener in self.__block_listeners.values():
            self.cancel_listen_state(listener)
        self.__block_listeners.clear()
        for timer in self.__block_timers:
            self.cancel_timer(timer)
        self.__block_timers.clear()

    def __block_on_state(self, entity, attribute, old, new, kwargs):
        if entity not in self.__block_listeners:
            return
        del self.__block_listeners[entity]
        Blocker.main_blocker.block()

    def unblock_until(self, when):
        self.__block_timers.append(
            self.run_once(self.__block, DateTimeUtil.to_time(when)))
        Blocker.main_blocker.unblock()

    def unblock_until_date_time(self, when):
        self.__block_timers.append(
            self.run_at(self.__block, self.__convert_date(when)))
        Blocker.main_blocker.unblock()

    def unblock_for(self, duration):
        self.__block_timers.append(
            self.run_in(self.__block, self.__convert_time(duration)))
        Blocker.main_blocker.unblock()

    def unblock_until_state_change(
            self, entity, timeout=None, deadline=None, **kwargs):
        # TODO: Use oneshot when home-assistant/appdaemon#299 is pulled
        self.__block_listeners[entity] = \
            self.listen_state(self.__block_on_state, entity, **kwargs)

        if timeout is not None:
            converted_timeout = self.__convert_time(timeout)
            if converted_timeout == 0:
                return
            self.unblock_for(converted_timeout)
            return

        if deadline is not None:
            converted_deadline = self.__convert_time(deadline)
            if DateTimeUtil.to_time(converted_deadline) == self.time():
                return
            self.unblock_until(deadline)
            return

        Blocker.main_blocker.unblock()

    def get_current_time(self):
        return self.datetime().timestamp()

    def schedule_call_at(self, when, data):
        self.run_once(self.__call, DateTimeUtil.to_time(when), **data)

    def schedule_call_in(self, delay, data):
        self.run_in(self.__call, self.__convert_time(delay), **data)

    def schedule_call_at_date_time(self, when, data):
        self.run_at(self.__call, self.__convert_date(when), **data)

    def is_blocked(self):
        return Blocker.main_blocker.is_blocked()

    def is_state_stable(self):
        return not Blocker.set_state_blocker.is_blocked()

    def call_on_app(self, app, function, *args, **kwargs):
        return getattr(self.get_app(app), function)(*args, **kwargs)

    def get_date(self):
        return self.datetime()

    def __state_set(self, entity, attribute, old, new, kwargs):
        self.log(
            'state changed: {}={} pending={}'.format(
                entity, new,
                ['{}->{}'.format(k, v.state)
                for k, v in self.__pending_states.items()]))
        pending_state = self.__pending_states.get(
            entity, self.PendingState())
        if pending_state.state != new:
            return
        self.cancel_listen_event(pending_state.listener)
        del self.__pending_states[entity]
        if len(self.__pending_states) == 0:
            Blocker.set_state_blocker.unblock()

    def wait_for_state_change(self, entity, state):
        old_state = self.get_state(entity)
        self.log(
            'state change initiated for {}: old={} target={}'.format(
                entity, old_state, state))
        if str(old_state) == str(state):
            return
        Blocker.set_state_blocker.block()
        pending_state = self.__pending_states.setdefault(
            entity, self.PendingState())
        pending_state.state = state
        if not pending_state.listener:
            pending_state.listener = self.listen_state(
                self.__state_set, entity)

    def set_sensor_state(self, entity, state, attributes=None):
        state = str(state)
        self.wait_for_state_change(entity, state)
        if not attributes:
            self.set_state(entity, state=state)
        else:
            self.set_state(entity, state=state, attributes=attributes)

    def select_option(self, entity, state):
        state = str(state)
        self.wait_for_state_change(entity, state)
        super(TestApp, self).select_option(entity_id=entity, option=state)

    def set_value(self, entity, state):
        state = float(state)
        self.wait_for_state_change(entity, str(state))
        super(TestApp, self).set_value(entity, state)

    def call_service_(self, service, target_entity, target_state, **kwargs):
        self.wait_for_state_change(target_entity, str(target_state))
        self.call_service(service, **kwargs)

    def turn_on(self, entity):
        self.wait_for_state_change(entity, 'on')
        super(TestApp, self).turn_on(entity)

    def turn_off(self, entity):
        self.wait_for_state_change(entity, 'off')
        super(TestApp, self).turn_off(entity)
