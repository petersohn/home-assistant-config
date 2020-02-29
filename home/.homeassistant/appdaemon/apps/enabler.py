import appdaemon.plugins.hass.hassapi as hass
import datetime


class Enabler(hass.Hass):
    def _init_enabler(self, state):
        self.log('init_enabler()')
        self.callbacks = []
        self.state = state
        self.state_mutex = self.get_app('locker').get_mutex('Enabler.State')
        self.callbacks_mutex = self.get_app('locker').get_mutex(
            'Enabler.Callbacks')
        self.log('Init: {}'.format(self.state))

    # This must not be called from within a callback!
    def _change(self, state):
        with self.callbacks_mutex.lock('_change'):
            callbacks = self.callbacks[:]
        with self.state_mutex.lock('_change'):
            if self.state != state:
                self.log('state change {} -> {}'.format(self.state, state))
                self.state = state
        for callback in callbacks:
            callback()

    def on_change(self, func):
        self.log('on_change()')
        with self.callbacks_mutex.lock('on_change'):
            self.callbacks.append(func)

    def is_enabled(self):
        self.log('is_enabled()')
        with self.state_mutex.lock('is_enabled'):
            assert self.state is not None
            return self.state


class ScriptEnabler(Enabler):
    def initialize(self):
        self._init_enabler(self.args.get('initial', True))

    def enable(self):
        self._change(True)

    def disable(self):
        self._change(False)


class EntityEnabler(Enabler):
    def initialize(self):
        self._entity = self.args['entity']
        self.listen_state(self._on_change, entity=self._entity)
        self.mutex = self.get_app('locker').get_mutex('EntityEnabler')
        self._init_enabler(self._get())

    def _on_change(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('_on_change'):
            self._change(self._get())

    def _get(self):
        return False


class ValueEnabler(EntityEnabler):
    def initialize(self):
        self.values = self.args.get('values')
        if not self.values:
            self.values = [self.args['value']]
        EntityEnabler.initialize(self)

    def _get(self):
        return self.get_state(self._entity) in self.values


def is_between(value, min_value, max_value):
        if min_value is not None and float(value) < min_value:
            return False
        if max_value is not None and float(value) > max_value:
            return False
        return True


class RangeEnabler(EntityEnabler):
    def initialize(self):
        self.__min = self.args.get('min')
        self.__max = self.args.get('max')
        EntityEnabler.initialize(self)

    def _get(self):
        value = self.get_state(self._entity)
        return is_between(value, self.__min, self.__max)


class DateEnabler(Enabler):
    def initialize(self):
        self.begin = datetime.datetime.strptime(
            self.args['begin'], '%m-%d').date()
        self.end = datetime.datetime.strptime(self.args['end'], '%m-%d').date()
        self._init_enabler(self._get())
        self.run_daily(
            lambda _: self._change(self._get()), datetime.time(0, 0, 1))

    def _get(self):
        now = self.date()
        begin = datetime.date(now.year, self.begin.month, self.begin.day)
        end = datetime.date(now.year, self.end.month, self.end.day)
        if begin <= end:
            return begin <= now <= end
        else:  # begin > end
            return now >= begin or now <= end


class HistoryEnabler(Enabler):
    def initialize(self):
        self._init_enabler(None)
        self.min = self.args.get('min')
        self.max = self.args.get('max')
        import history
        self.aggregator = history.Aggregator(self, self.set_value)

    def set_value(self, value):
        enabled = is_between(value, self.min, self.max)
        self._change(enabled)


class MultiEnabler(Enabler):
    def initialize(self):
        self.enablers = [
            self.get_app(enabler) for enabler in self.args.get('enablers')]
        self.mutex = self.get_app('locker').get_mutex('MultiEnabler')
        self._init_enabler(self.__get())
        for enabler in self.enablers:
            enabler.on_change(lambda: self._on_change())

    def _on_change(self):
        self.run_in(self.get, 0)

    def get(self, kwargs):
        with self.mutex.lock('get'):
            self._change(self.__get())

    def __get(self):
        return all([enabler.is_enabled() for enabler in self.enablers])


class ExpressionEnabler(Enabler):
    def initialize(self):
        self.log('init')
        self.expr = self.args['expr']
        entities = set()
        enablers = set()

        self.mutex = self.get_app('locker').get_mutex('ExpressionEnabler')

        def e(name):
            enablers.add(name)
            return self._get_enabled(name)

        def v(name):
            entities.add(name)
            return self._get_value(name)

        value = eval(self.expr, self._create_evaluators(e, v))
        self.evaluators = self._create_evaluators(
            self._get_enabled, self._get_value)
        for entity in entities:
            self.listen_state(self.get, entity=entity)
        for enabler in enablers:
            self.log('-> {}'.format(enabler))
            self.get_app(enabler).on_change(lambda: self._on_enabler_change())
        self._init_enabler(value)

    def _create_evaluators(self, e, v):
        class Evaluator:
            def __init__(self, func):
                self.__func = func

            def __getattr__(self, value):
                return self.__func(value)

        return {'e': Evaluator(e), 'v': Evaluator(v)}

    def _get_value(self, entity):
        self.log('--> get_value {}'.format(entity))
        value = self.get_state(entity)
        try:
            return float(value)
        except ValueError:
            return value

    def _get_enabled(self, enabler):
        value = self.get_app(enabler).is_enabled()
        self.log('get_enabled({}) = {}'.format(enabler, value))
        return value

    def _on_enabler_change(self):
        self.log('_on_enabler_change()')
        self.run_in(self.get, 0)

    def _on_entity_change(self, entity, attribute, old, new, kwargs):
        if new != old:
            self.get()

    def get(self, kwargs):
        self.log('get()')
        with self.mutex.lock('get'):
            value = eval(self.expr, self.evaluators)
            self._change(value)
