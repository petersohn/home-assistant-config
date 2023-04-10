import appdaemon.plugins.hass.hassapi as hass
import datetime

import expression


class CoverController(hass.Hass):
    def initialize(self):
        self.target = self.args['target']
        self.mutex = self.get_app('locker').get_mutex('CoverController')

        self.expression = expression.ExpressionEvaluator(
            self, self.args['expr'], self.on_expression_change)
        self.value = self.expression.get()

        delay = self.args.get('delay')
        self.delay = datetime.timedelta(**delay) if delay is not None else None
        self.timer = None

    def cleanup(self):
        self.expression.cleanup()

    def _set_value(self, value):
        self.log('Changing to {}'.format(value))
        if type(value) is float or type(value) is int:
            if value >= 0 and value <= 100:
                self.call_service(
                    'cover/set_cover_position',
                    entity_id=self.target,
                    position=int(value))
                return
        elif type(value) is str:
            lower = value.lower()
            if lower == 'open':
                self.call_service('cover/open_cover', entity_id=self.target)
                return
            if lower == 'closed':
                self.call_service('cover/close_cover', entity_id=self.target)
                return

        self.log('Invalid value: {}'.format(value))

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
