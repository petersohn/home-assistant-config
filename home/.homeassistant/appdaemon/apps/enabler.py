import appdaemon.plugins.hass.hassapi as hass
import datetime


class Enabler(hass.Hass):
    def _init_enabler(self, state):
        self.__callbacks = []
        self.__state = state

    def _change(self, state):
        if self.__state != state:
            self.__state = state
            for callback in self.__callbacks:
                callback(state)

    def on_change(self, func):
        self.__callbacks.append(func)

    def is_enabled(self):
        return self.__state


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
        self.listen_state(self.__on_change, entity=self._entity)
        self._init_enabler(self._get())

    def __on_change(self, entity, attribute, old, new, kwargs):
        self._change(self._get())

    def _get(self):
        return False


class ValueEnabler(EntityEnabler):
    def initialize(self):
        self.__values = self.args.get('values')
        if not self.__values:
            self.__values = [self.args['value']]
        EntityEnabler.initialize(self)

    def _get(self):
        return self.get_state(self._entity) in self.__values


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
        self.__begin =\
            datetime.datetime.strptime(self.args['begin'], '%m-%d').date()
        self.__end =\
            datetime.datetime.strptime(self.args['end'], '%m-%d').date()
        self._init_enabler(self._get())
        self.run_daily(
            lambda _: self._change(self._get()), datetime.time(0, 0, 1))

    def _get(self):
        now = self.date()
        begin = datetime.date(now.year, self.__begin.month, self.__begin.day)
        end = datetime.date(now.year, self.__end.month, self.__end.day)
        if begin <= end:
            return begin <= now <= end
        else:  # begin > end
            return now >= begin or now <= end


class HistoryEnabler(Enabler):
    def initialize(self):
        self.__min = self.args.get('min')
        self.__max = self.args.get('max')
        self.__initialized = False
        import history
        self.__aggregator_app = history.AggregatorApp(self, self.__set_value)

    def __set_value(self, value):
        enabled = is_between(value, self.__min, self.__max)
        if not self.__initialized:
            self._init_enabler(enabled)
        else:
            self._changed(enabled)


class MultiEnabler:
    def __init__(self, app, enablers):
        self.__enablers = [app.get_app(enabler) for enabler in enablers]

    def is_enabled(self):
        return all([enabler.is_enabled() for enabler in self.__enablers])
