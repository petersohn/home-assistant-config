import appdaemon.plugins.hass.hassapi as hass
import expression

class AlertAggregator(hass.Hass):
    class Source:
        def __init__(self, app, entity, trigger_expr, text_expr):
            self.app = app
            self.entity = entity
            extra_values = {'name': entity}
            self.trigger_expr = expression.ExpressionEvaluator(
                app, trigger_expr, self._on_change, extra_values)
            self.text_expr = expression.ExpressionEvaluator(
                app, text_expr, None, extra_values)
            self.value = self._calculate_trigger_value()

        def _on_change(self, value):
            self.value = value
            self.app.on_change(self.entity, value)

        def cleanup(self):
            self.trigger_expr.cleanup()
            self.text_expr.cleanup()

        def get_trigger_value(self):
            return self.value

        def _calculate_trigger_value(self):
            val = self.trigger_expr.get()
            return val

        def get_text_value(self):
            return self.text_expr.get()

    def initialize(self):
        self.target = self.args['target']
        trigger_expr = self.args['trigger_expr']
        text_expr = self.args['text_expr']
        self.sources = [
            self.Source(self, entity, trigger_expr, text_expr)
            for entity in self.args['sources']]
        self._turn_off()
        if any(source.get_trigger_value() for source in self.sources):
            self.log('Alert is initially on')
            self._turn_on()

    def terminate(self):
        for source in self.sources:
            source.cleanup()

    def _turn_off(self):
        self.set_state(self.target, state='off', attributes={'text': ''})

    def _turn_on(self):
        self.set_state(self.target, state='on', attributes={
            'text': '\n'.join(
                source.get_text_value()
                for source in self.sources
                if source.get_trigger_value())})

    def on_change(self, entity, value):
        if value:
            self.log('Alert turned on for {}'.format(entity))
            self._turn_off()
            self._turn_on()
            return

        if not any(source.get_trigger_value() for source in self.sources):
            self.log('Resetting alert')
            self._turn_off()
            return

        self.log('Setting alert')
        self._turn_on()
