import appdaemon.plugins.hass.hassapi as hass

import auto_switch


class EnabledSwitch(hass.Hass):
    def initialize(self):
        self.mutex = self.get_app('locker').get_mutex('EnabledSwitch')
        self.enabler = self.get_app(self.args['enabler'])
        self.targets = auto_switch.MultiSwitcher(self, self.args['targets'])
        self.enabler.on_change(self.set_state)
        if self.enabler.is_enabled():
            self.run_in(lambda _: self.targets.turn_on(), 0)

    def terminate(self):
        self.targets.turn_off()

    def set_state(self):
        with self.mutex.lock('set_state'):
            if self.enabler.is_enabled():
                self.targets.turn_on()
            else:
                self.targets.turn_off()
