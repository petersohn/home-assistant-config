import appdaemon.plugins.hass.hassapi as hass


class TestOtherApp(hass.Hass):
    def initialze(self):
        pass

    def other_test(self, arg):
        return arg
