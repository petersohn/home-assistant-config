import appdaemon.plugins.hass.hassapi as hass


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


class RangeEnabler(hass.Hass):
    def initialize(self):
        self.__entity = self.args['entity']
        self.__min = self.args.get('min')
        self.__max = self.args.get('max')

    def is_enabled(self):
        value = self.get_state(self.__entity)
        if self.__min is not None and float(value) < self.__min:
            return False
        if self.__max is not None and float(value) > self.__max:
            return False
        return True


class SunEnabler(hass.Hass):
    def initialize(self):
        self.__day = self.args.get('day', True)

    def is_enabled(self):
        return ((self.__day and self.sun_up()) or
                (not self.__day and self.sun_down()))
