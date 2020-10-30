import appdaemon.plugins.hass.hassapi as hass
import expression

class AlertAggregator(hass.Hass):
    class Source:
        def __init__(self, entity, trigger_expr, text_expr):
            self.entity = entity

    def initialize(self):
        self.target_sensor = self.args['target_sensor']
        self.target_text = self.args['target_text']
        trigger_expr = self.args['trigger_expr']
        text_expr = self.args['text_expr']
        self.sources = [
            Source(entity, trigger_expr, text_expr) 
            for entity in self.args['sources']]
