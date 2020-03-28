import appdaemon.plugins.hass.hassapi as hass
import datetime


class ExpressionEvaluator:
    def __init__(self, app, expr, callback):
        self.mutex = app.get_app('locker').get_mutex('ExpressionEvaluator')

        self.app = app
        self.expr = expr
        self.callback = callback
        self.entities = set()
        self.enablers = set()
        self.evaluators = self._create_evaluators(
            self._get_enabled, self._get_value)

    def _create_evaluators(self, e, v):
        class Evaluator:
            def __init__(self, func):
                self.__func = func

            def __getattr__(self, value):
                return self.__func(value)

            def __getitem__(self, value):
                return self.__func(str(value))

        return {'e': Evaluator(e), 'v': Evaluator(v)}

    def _get_value(self, entity):
        if entity not in self.entities:
            self.app.listen_state(self._on_entity_change, entity=entity)
            self.entities.add(entity)
        value = self.app.get_state(entity)
        self.app.log('_get_value: {} = {}'.format(entity, value))
        if value == 'on':
            return True
        if value == 'off':
            return False
        try:
            return float(value)
        except ValueError:
            return value

    def _get_enabled(self, enabler):
        app = self.app.get_app(enabler)
        if enabler not in self.enablers:
            app.on_change(lambda: self._on_enabler_change())
            self.enablers.add(enabler)
        value = app.is_enabled()
        return value

    def _on_enabler_change(self):
        self.app.run_in(self.fire_callback, 0)

    def _on_entity_change(self, entity, attribute, old, new, kwargs):
        self.app.log('state change({}): {} -> {}'.format(entity, old, new))
        if new != old:
            self.fire_callback({})

    def _get(self):
        return eval(self.expr, self.evaluators)

    def get(self):
        with self.mutex.lock('get'):
            return self._get()

    def fire_callback(self, kwargs):
        with self.mutex.lock('fire_callback'):
            value = self._get()
            self.callback(value)
