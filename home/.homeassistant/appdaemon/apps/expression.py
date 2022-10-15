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


def filter_nums(*args):
    return filter(lambda x: type(x) == float, args)


class ExpressionEvaluator:
    def __init__(self, app, expr, callback=None, extra_values={}):
        self.mutex = app.get_app('locker').get_mutex('ExpressionEvaluator')

        self.app = app
        self.expr = expr
        self.callback = callback
        self.entities = set()
        self.attributes = set()
        self.app_callbacks = {}
        self.evaluators = self._create_evaluators()
        self.evaluators.update(extra_values)
        self.timer = None
        self.get()

    def cleanup(self):
        for name, id in self.app_callbacks.items():
            try:
                self.app.get_app(name).remove_callback(id)
            except:
                self.app.error(traceback.format_exc())

    def _create_evaluators(self):
        return {
            'a': Evaluator(self._get_attribute_base),
            'e': Evaluator(self._get_enabled),
            'c': Evaluator(self._get_last_changed),
            'u': Evaluator(self._get_last_updated),
            'v': Evaluator(self._get_value),
            'ok': Evaluator(self._get_ok),
            'now': self._get_now,
            'strptime': datetime.datetime.strptime,
            'dt': datetime.timedelta,
            't': datetime.datetime,
            'nums': filter_nums,
            'args': self.app.args,
        }

    def _get_now(self):
        now_ts = int(self.app.get_now_ts())
        if self.callback is not None and self.timer is None:
            self.timer = self.app.run_every(
                self.fire_callback,
                datetime.datetime.fromtimestamp(now_ts + 1), 1)
        return datetime.datetime.fromtimestamp(now_ts)

    def _get_attribute_base(self, entity):
        if '.' not in entity:
            return Evaluator(self._get_attribute_base, entity + '.')
        return Evaluator(self._get_attribute_callback(entity))

    def _get_attribute_callback(self, entity):
        return lambda attribute: self._get_attribute(entity, attribute)

    def _get_attribute(self, entity, attribute):
        key = (entity, attribute)
        if self.callback is not None and key not in self.attributes:
            self.app.listen_state(
                self._on_entity_change, entity=entity, attribute=attribute)
            self.attributes.add(key)

        value = self.app.get_state(entity, attribute=attribute)
        if value is None:
            return ''
        try:
            return float(value)
        except ValueError:
            return value

    def _get_value(self, entity):
        if '.' not in entity:
            return Evaluator(self._get_value, entity + '.')

        if self.callback is not None and entity not in self.entities:
            self.app.listen_state(self._on_entity_change, entity=entity)
            self.entities.add(entity)
        value = self.app.get_state(entity)
        if value is None:
            return ''
        if value == 'on':
            return True
        if value == 'off':
            return False
        try:
            return float(value)
        except ValueError:
            return value

    def _get_ok(self, entity):
        if '.' not in entity:
            return Evaluator(self._get_ok, entity + '.')

        if self.callback is not None and entity not in self.entities:
            self.app.listen_state(self._on_entity_change, entity=entity)
            self.entities.add(entity)
        value = self.app.get_state(entity)
        return value != 'unknown' and value != 'unavailable'

    def _get_app(self, name):
        app = self.app.get_app(name)
        if self.callback is not None and name not in self.app_callbacks:
            id = app.add_callback(lambda: self._on_app_change())
            self.app_callbacks[name] = id
        return app

    def _get_enabled(self, name):
        return self._get_app(name).is_enabled()

    def _get_last_changed(self, name):
        return self._get_app(name).last_changed()

    def _get_last_updated(self, name):
        return self._get_app(name).last_updated()

    def _on_app_change(self):
        self.app.log('on_app_change')
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
            return
        with self.mutex.lock('fire_callback'):
            value = self._get()
            self.callback(value)


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
        if type(value) is bool:
            value = 'on' if value else 'off'
        self.set_state(self.target, state=value, attributes=self.attributes)
