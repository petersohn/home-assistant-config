import appdaemon.plugins.hass.hassapi as hass


class TestOtherApp(hass.Hass):
    def initialize(self):
        pass

    def other_test(self, arg):
        return arg
