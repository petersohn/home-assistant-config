import appdaemon.plugins.hass.hassapi as hass
import datetime
import traceback


class Evaluator:
    def __init__(self, func, prefix=''):
        self.__prefix = prefix
        self.__func = func

    def __getattr__(self, value):
        return self.__func(self.__prefix + value)

    def __getitem__(self, value):
        return self.__func(self.__prefix + str(value))


class ExpressionEvaluator:
    def __init__(self, app, expr, callback, extra_values={}):
        self.mutex = app.get_app('locker').get_mutex('ExpressionEvaluator')

        self.app = app
        self.expr = expr
        self.callback = callback
        self.entities = set()
        self.enablers = {}
        self.evaluators = self._create_evaluators()
        self.evaluators.update(extra_values)
        self.timer = None
        self.get()

    def cleanup(self):
        for enabler, id in self.enablers.items():
            self.app.get_app(enabler).remove_callback(id)

    def _create_evaluators(self):
        return {
            'e': Evaluator(self._get_enabled),
            'v': Evaluator(self._get_value),
            'now': self._get_now,
            'strptime': datetime.datetime.strptime,
            'strftime': datetime.datetime.strftime,
            'dt': datetime.timedelta,
            't': datetime.datetime,
            'args': self.app.args,
        }

    def _get_now(self):
        now_ts = int(self.app.get_now_ts())
        if self.callback is not None and self.timer is None:
            self.timer = self.app.run_every(
                self.fire_callback,
                datetime.datetime.fromtimestamp(now_ts + 1), 1)
        return datetime.datetime.fromtimestamp(now_ts)

    def _get_value(self, entity):
        if '.' not in entity:
            return Evaluator(self._get_value, entity + '.')

        if self.callback is not None and entity not in self.entities:
            self.app.listen_state(self._on_entity_change, entity=entity)
            self.entities.add(entity)
        value = self.app.get_state(entity)
        if value == 'on':
            return True
        if value == 'off':
            return False
        try:
            return float(value)
        except ValueError:
            return value

    def _get_enabled(self, enabler):
        enabler_app = self.app.get_app(enabler)
        if self.callback is not None and enabler not in self.enablers:
            id = enabler_app.on_change(lambda: self._on_enabler_change())
            self.enablers[enabler] = id
        value = enabler_app.is_enabled()
        return value

    def _on_enabler_change(self):
        self.app.run_in(self.fire_callback, 0)

    def _on_entity_change(self, entity, attribute, old, new, kwargs):
        self.app.log('state change({}): {} -> {}'.format(entity, old, new))
        if new != old:
            self.fire_callback({})

    def _get(self):
        try:
            return eval(self.expr, self.evaluators)
        except:
            self.app.error(traceback.format_exc())
            self.app.run_in(lambda _: self.get(), 60)
            return None

    def get(self):
        with self.mutex.lock('get'):
            return self._get()

    def fire_callback(self, kwargs):
        if self.callback is None:
            self.app.log('No callback')
            return
        self.app.log('begin')
        with self.mutex.lock('fire_callback'):
            self.app.log('got lock')
            value = self._get()
            self.app.log('callback')
            self.callback(value)
            self.app.log('end')


class Expression(hass.Hass):
    def initialize(self):
        self.target = self.args['target']
        self.attributes = self.args.get('attributes', {})
        self.evaluator = ExpressionEvaluator(
            self, self.args['expr'], self._set)
        self._set(self.evaluator.get())

    def terminate(self):
        self.evaluator.cleanup()

    def _set(self, value):
        self.set_state(self.target, state=value, attributes=self.attributes)
