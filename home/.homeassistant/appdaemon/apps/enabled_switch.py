import appdaemon.plugins.hass.hassapi as hass

import auto_switch


class EnabledSwitch(hass.Hass):
    def initialize(self):
        self.enabler = self.get_app(self.args['enabler'])
        self.targets = auto_switch.MultiSwitcher(self, self.args['targets'])
        self.enabler.on_change(self.set_state)

    def set_state(self, state):
        if state:
            self.targets.turn_on()
        else:
            self.targets.turn_off()
