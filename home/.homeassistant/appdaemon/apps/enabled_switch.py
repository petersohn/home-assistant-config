import appdaemon.plugins.hass.hassapi as hass

import auto_switch


class EnabledSwitch(hass.Hass):
    def initialize(self):
        self.__enabler = self.get_app(self.args['enabler'])
        self.__targets = auto_switch.MultiSwitcher(self, self.args['targets'])
        self.__enabler.on_change(self.__set_state)

    def __set_state(self, state):
        if state:
            self.__targets.turn_on()
        else:
            self.__targets.turn_off()
