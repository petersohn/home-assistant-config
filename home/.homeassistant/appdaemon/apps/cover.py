import appdaemon.plugins.hass.hassapi as hass
import datetime

import expression

class CoverController(hass.Hass):
    class Mode:
        AUTO = 0
        MANUAL = 1
        TEMP = 2

    def initialize(self):
        self.target = self.args['target']
        self.mutex = self.get_app('locker').get_mutex('CoverController')

        self.expression = expression.ExpressionEvaluator(
            self, self.args['expr'], self.on_expression_change)
        self.value = self.expression.get()
        self.expected_value = None

        delay = self.args.get('delay')
        self.delay = datetime.timedelta(**delay) if delay is not None else None
        self.timer = None

        self.mode_switch = self.args.get('mode_switch')
        if self.mode_switch is not None:
            mode = self.get_state(self.mode_switch)
            if mode == 'temp':
                self._set_mode(self.Mode.AUTO)
            else:
                self._set_mode_from_str(mode)
            self.listen_state(self.on_mode_change, entity=self.mode_switch)
        else:
            self.mode = self.Mode.AUTO

        state = self.get_state(self.target)
        self.is_available = state != 'unavailable'
        self.listen_state(
            self.on_state_change, entity=self.target, attribute='all')

        self.target_position = None

    def cleanup(self):
        self.expression.cleanup()

    def _set_mode(self, state):
        self.mode = state

        if self.mode_switch is None:
            return

        if state == self.Mode.AUTO:
            self.select_option(self.mode_switch, 'auto')
        elif state == self.Mode.MANUAL:
            self.select_option(self.mode_switch, 'manual')
        elif state == self.Mode.TEMP:
            self.select_option(self.mode_switch, 'temp')
        else:
            self.error('Invalid state: {}'.format(state))
            self.mode = self.Mode.AUTO

    def _set_mode_from_str(self, mode):
        if mode == 'auto':
            self.mode = self.Mode.AUTO
        elif mode == 'manual':
            self.mode = self.Mode.MANUAL
        elif mode == 'temp':
            self.mode = self.Mode.TEMP
        else:
            self.error('Invalid mode: {}'.format(mode))
            self._set_mode(self.Mode.AUTO)

    def _execute(self, service, **kwargs):
        kwargs['entity_id'] = self.target
        self.call_service(service, **kwargs)

    def _reset_value(self):
        self._set_value(self.expected_value)

    def _set_value_inner(self, value):
        if type(value) is float or type(value) is int:
            if value >= 0 and value <= 100:
                self._execute(
                    'cover/set_cover_position',
                    position=int(value))
                self.target_position = value
                return
        elif type(value) is str:
            lower = value.lower()
            if lower == 'open':
                self._execute('cover/open_cover')
                self.target_position = 100
                return
            if lower == 'closed':
                self._execute('cover/close_cover')
                self.target_position = 0
                return

        self.log('Invalid value: {}'.format(value))

    def _set_value(self, value):
        self.log('Changing to {}'.format(value))

        if self.expected_value != value and self.mode == self.Mode.TEMP:
            self.log('Setting mode back to auto')
            self._set_mode(self.Mode.AUTO)

        self.expected_value = value

        if not self.is_available:
            self.log('Not available')
            return

        if self.mode != self.Mode.AUTO:
            self.log('Not in auto mode')
            return

        self._set_value_inner(value)
        self._check_state(self.get_state(self.target, attribute='all'))

    def on_expression_change(self, value):
        with self.mutex.lock('on_expression_change'):
            self.log('Value changed: {} -> {}'.format(self.value, value))
            if self.value == value:
                return

            self.value = value

            if self.delay is None:
                self._set_value(value)
                return

            if self.timer is not None:
                self.cancel_timer(self.timer)
                self.timer = None

            self.timer = self.run_in(
                self.on_delay, self.delay.total_seconds(), value=value)

    def on_delay(self, kwargs):
        with self.mutex.lock('on_expression_change'):
            self.timer = None
            self._set_value(kwargs['value'])

    def on_state_change(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('on_state_change'):
            # self.log('--> {}'.format(new))
            self._check_state(new)

    def _check_state(self, states):
        state = states['state']
        was_available = self.is_available
        is_available = \
            state is not None and \
            state != 'unknown' and \
            state != 'unavailable'
        self.is_available = is_available

        if not was_available and is_available:
            self.log('Became available')
            self._reset_value()
        elif was_available and not is_available:
            self.log('Became unavailable')

        if not self.is_available:
            self.target_position = None
            return

        is_moving = state == 'opening' or state == 'closing'
        if self.target_position is not None:
            position = int(states['attributes']['current_position'])
            if not is_moving:
                if position == self.target_position:
                    self.log('Reached target position')
                    self.target_position = None
                else:
                    self.log('Stopped at {}, changing to temp'.format(position))
                    self._set_mode(self.Mode.TEMP)
        elif is_moving and self.mode == self.Mode.AUTO:
            self.log('Started {}, changing to temp'.format(state))
            self._set_mode(self.Mode.TEMP)

    def on_mode_change(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('on_mode_change'):
            if old != new:
                self.log('New mode: {}').format(new)
                self._set_mode_from_str(new)
                if self.mode == self.Mode.AUTO:
                    self.log('Back to auto, resetting value.')
                    self._reset_value()
                else:
                    self.target_position = None
