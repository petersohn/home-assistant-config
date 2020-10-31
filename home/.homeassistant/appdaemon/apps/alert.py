import appdaemon.plugins.hass.hassapi as hass
import expression

class AlertAggregator(hass.Hass):
    class Source:
        def __init__(self, app, entity, trigger_expr, text_expr, callback):
            self.app = app
            self.entity = entity
            extra_evaluators = {'value': _self.get_value}
            self.trigger_expr = expression.ExpressionEvaluator(
                app, trigger_expr, self.app.on_change(),
                extra_evaluators)
            self.text_expr = expression.ExpressionEvaluator(
                app, text_expr, None, extra_evaluators)

        def cleanup(self):
            self.trigger_expr.cleanup()
            self.text_expr.cleanup()

        def _get_value(self):
            return self.app.get_state(self.entity)

        def get_trigger_value(self):
            return self.trigger_expr.get()

        def get_text_value(self):
            return self.text_expr.get()

    def initialize(self):
        self.target = self.args['target']
        trigger_expr = self.args['trigger_expr']
        text_expr = self.args['text_expr']
        self.sources = [
            Source(entity, trigger_expr, text_expr)
            for entity in self.args['sources']]

    def terminate(self):
        for source in self.sources:
            source.cleanup()

    def _turn_off(self):
        self.target.set_state(state='off', attributes={'text': ''})

    def on_change(self, value):
        if not any(source.get_trigger_value() for source in self.sources):
            self.turn_off()
            return

        if value:
            self.turn_off()
        self.target.set_state(state='on', attributes={
            'text': '\n'.join(
                source.get_text_value()
                for source in self.sources
                if source.get_trigger_value())})

