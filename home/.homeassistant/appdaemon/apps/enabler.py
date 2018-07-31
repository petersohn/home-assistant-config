import appdaemon.plugins.hass.hassapi as hass
import datetime


class ScriptEnabler(hass.Hass):
    def initialize(self):
        self.__enabled = self.args.get('initial', True)

    def enable(self):
        self.__enabled = True

    def disable(self):
        self.__enabled = False

    def is_enabled(self):
        return self.__enabled


class ValueEnabler(hass.Hass):
    def initialize(self):
        self.__entity = self.args['entity']
        self.__values = self.args.get('values')
        if not self.__values:
            self.__values = [self.args['value']]

    def is_enabled(self):
        return self.get_state(self.__entity) in self.__values


def is_between(value, min_value, max_value):
        if min_value is not None and float(value) < min_value:
            return False
        if max_value is not None and float(value) > max_value:
            return False
        return True


class RangeEnabler(hass.Hass):
    def initialize(self):
        self.__entity = self.args['entity']
        self.__min = self.args.get('min')
        self.__max = self.args.get('max')

    def is_enabled(self):
        value = self.get_state(self.__entity)
        return is_between(value, self.__min, self.__max)


class SunEnabler(hass.Hass):
    def initialize(self):
        self.__day = self.args.get('day', True)

    def is_enabled(self):
        return ((self.__day and self.sun_up()) or
                (not self.__day and self.sun_down()))


class HistoryEnabler(hass.Hass):
    def initialize(self):
        self.__manager = self.get_app(self.args['manager'])
        self.__aggregator = eval(self.args['aggregator'], {}, {})
        self.__default = self.args.get('default')
        if 'interval' in self.args:
            self.__interval = datetime.timedelta(**self.args['interval'])
        else:
            self.__interval = None
        self.__min = self.args.get('min')
        self.__max = self.args.get('max')

    def is_enabled(self):
        values = []
        for value in self.__manager.get_values(self.__interval):
            try:
                values.append(float(value))
            except ValueError:
                pass
        if not values:
            if self.__default is not None:
                values = [self.__default]
            else:
                values = self.__manager.get_values()[-1:]
        aggregated_value = self.__aggregator(values)
        return is_between(aggregated_value, self.__min, self.__max)
