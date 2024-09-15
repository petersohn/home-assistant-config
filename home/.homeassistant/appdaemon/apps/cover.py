import appdaemon.plugins.hass.hassapi as hass
import datetime

import expression

class CoverController(hass.Hass):
    class Mode:
        AUTO = 0
        MANUAL = 1
        STABLE = 2

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

        with self.mutex.lock('initialize'):
            self.mode_switch = self.args.get('mode_switch')
            if self.mode_switch is not None:
                mode = self.get_state(self.mode_switch)
                if mode == 'stable':
                    self._set_mode(self.Mode.AUTO)
                else:
                    self._set_mode_from_str(mode)
                self.listen_state(self.on_mode_change, entity=self.mode_switch)
            else:
                self.mode = self.Mode.AUTO

            state = self.get_state(self.target)
            self.is_available = state is not None and state != 'unavailable'
            self.listen_state(
                self.on_state_change, entity=self.target, attribute='all')
            self._reset_target()
            if self.is_available and \
                    self.mode == self.Mode.AUTO \
                    and self.value is not None:
                self._set_value(self.value)
            else:
                self.expected_value = self.value

    def terminate(self):
        self.expression.cleanup()

    def _set_mode(self, state):
        self.mode = state

        if self.mode_switch is None:
            return

        if state == self.Mode.AUTO:
            self.select_option(self.mode_switch, 'auto')
        elif state == self.Mode.MANUAL:
            self.select_option(self.mode_switch, 'manual')
        elif state == self.Mode.STABLE:
            self.select_option(self.mode_switch, 'stable')
        else:
            self.error('Invalid state: {}'.format(state))
            self.mode = self.Mode.AUTO

    def _set_mode_from_str(self, mode):
        if mode == 'auto':
            self.mode = self.Mode.AUTO
        elif mode == 'manual':
            self.mode = self.Mode.MANUAL
        elif mode == 'stable':
            self.mode = self.Mode.STABLE
        else:
            self.log('Invalid mode: {}'.format(mode))
            self._set_mode(self.Mode.STABLE)

    def _execute(self, service, **kwargs):
        kwargs['entity_id'] = self.target
        self.call_service(service, **kwargs)

    def _reset_value(self):
        self._set_value(self.expected_value)

    def _set_value_inner(self, value):
        self.log('Execute command: {}'.format(value))
        self.arrived_at_target = None
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

        if self.expected_value != value and self.mode == self.Mode.STABLE:
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
        self._force_check_state()

    def _force_check_state(self):
        self._check_state(self.get_state(self.target, attribute='all'))

    def on_expression_change(self, value):
        with self.mutex.lock('on_expression_change'):
            if self.value == value:
                self.log('Value unchanged: {}'.format(value))
                return

            self.log('Value changed: {} -> {}'.format(self.value, value))
            self.value = value

            if self.delay is None:
                self._set_value(value)
                return

            if self.timer is not None:
                self.log('Reset timer')
                self.cancel_timer(self.timer)
                self.timer = None

            self.timer = self.run_in(
                self.on_delay, self.delay.total_seconds(), value=value)

    def on_delay(self, kwargs):
        with self.mutex.lock('on_expression_change'):
            self.log('Time is up')
            self.timer = None
            self._set_value(kwargs['value'])

    def on_state_change(self, entity, attribute, old, new, kwargs):
        def _get_state(state):
            return state.get('state') if state is not None else None

        with self.mutex.lock('on_state_change'):
            if old is None or old['state'] != new['state']:
                self.log('State changed: {} -> {}'.format(
                    _get_state(old), _get_state(new)))
            if new is not None:
                self._check_state(new)

    def _check_state(self, states):
        # self.log('--> {}'.format(states))
        state = states['state']
        was_available = self.is_available
        is_available = \
            state is not None and \
            state != 'unavailable'
        self.is_available = is_available

        if not was_available and is_available:
            self.log('Became available')
            self._reset_value()
        elif was_available and not is_available:
            self.log('Became unavailable')
        elif state == 'unknown' and \
                self.mode == self.Mode.AUTO and \
                self.expected_value is not None:
            self.log('State unknown, need to reset.')
            self._reset_value()
            return

        if not self.is_available or self.mode != self.Mode.AUTO:
            self._reset_target()
            return

        current_position = states['attributes'].get('current_position')
        if current_position is None:
            self.log('Cannot determine current position')
            return

        is_moving = state == 'opening' or state == 'closing'
        if self.target_position is not None:
            position = int(current_position)
            # None or False
            if not self.arrived_at_target and \
                    not is_moving and \
                    position == self.target_position:
                self.log('Arrived at target')
                self.arrived_at_target = True
                self._set_mode(self.Mode.STABLE)
            elif self.arrived_at_target is None and is_moving:
                self.log('Started moving')
                self.arrived_at_target = False
            elif self.arrived_at_target is False and not is_moving:
                self.log('Stopped at {}, force resetting'.format(position))
                self._reset_value()
        else:
            self.log('Position not yet set')

    def on_mode_change(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('on_mode_change'):
            if old != new:
                self.log('New mode: {} -> {}'.format(old, new))
                self._set_mode_from_str(new)
                if self.mode == self.Mode.AUTO:
                    self.log('Back to auto, resetting value.')
                    self._reset_value()
                else:
                    self._reset_target()

    def _reset_target(self):
        self.target_position = None
        self.arrived_at_target = None
