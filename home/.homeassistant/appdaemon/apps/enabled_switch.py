import appdaemon.plugins.hass.hassapi as hass
import datetime

import auto_switch
import enabler


class EnabledSwitch(hass.Hass):
    def initialize(self):
        self.poll_interval = datetime.timedelta(
            **self.args.get('poll_interval', {'minutes': 1}))
        self.__enablers = enabler.MultiEnabler(
            self, self.args['enablers'])
        self.__targets = auto_switch.MultiSwitcher(self, self.args['targets'])
        self.run_every(
            lambda _: self.__set_state(), self.datetime(),
            self.poll_interval.seconds)

    def __set_state(self):
        if self.__enablers.is_enabled():
            self.__targets.turn_on()
        else:
            self.__targets.turn_off()
