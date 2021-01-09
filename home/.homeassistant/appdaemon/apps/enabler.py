import appdaemon.plugins.hass.hassapi as hass
import datetime


class Enabler(hass.Hass):
    def _init_enabler(self, state):
        self.callbacks = {}
        self.callback_id = 0
        self.state = state
        self.state_mutex = self.get_app('locker').get_mutex('Enabler.State')
        self.callbacks_mutex = self.get_app('locker').get_mutex(
            'Enabler.Callbacks')
        self.log('Init: {}'.format(self.state))

    # This must not be called from within a callback!
    def _change(self, state):
        with self.callbacks_mutex.lock('_change'):
            callbacks = list(self.callbacks.values())
        with self.state_mutex.lock('_change'):
            if self.state != state:
                self.log('state change {} -> {}'.format(self.state, state))
                self.state = state
        for callback in callbacks:
            callback()

    def add_callback(self, func):
        with self.callbacks_mutex.lock('add_callback'):
            id = self.callback_id
            self.callbacks[id] = func
            self.callback_id += 1
            return id

    def remove_callback(self, id):
        with self.callbacks_mutex.lock('remove_callback'):
            del self.callbacks[id]

    def is_enabled(self):
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
        self.ids = []
        for enabler in self.enablers:
            self.ids.append(enabler.add_callback(lambda: self._on_change()))

    def terminate(self):
        for enabler, id in zip(self.enablers, self.ids):
            enabler.remove_callback(id)

    def _on_change(self):
        self.run_in(self.get, 0)

    def get(self, kwargs):
        with self.mutex.lock('get'):
            self._change(self.__get())

    def __get(self):
        return all([enabler.is_enabled() for enabler in self.enablers])


class ExpressionEnabler(Enabler):
    def initialize(self):
        import expression
        self.evaluator = expression.ExpressionEvaluator(
            self, self.args['expr'], self._change)
        self._init_enabler(self.evaluator.get())

    def terminate(self):
        self.evaluator.cleanup()
