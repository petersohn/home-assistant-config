import appdaemon.plugins.hass.hassapi as hass
import expression


class CoverController(hass.Hass):
    def initialize(self):
        self.target = self.args['target']
        self.mutex = self.get_app('locker').get_mutex('CoverController')
        self.expression = expression.ExpressionEvaluator(
            self, self.args['expr'], self.on_expression_change)
        self.value = self.expression.get()

    def cleanup(self):
        self.expression.cleanup()

    def on_expression_change(self, value):
        self.log('Value changed: {} -> {}'.format(self.value, value))
        if self.value == value:
            return

        if type(value) is float:
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
