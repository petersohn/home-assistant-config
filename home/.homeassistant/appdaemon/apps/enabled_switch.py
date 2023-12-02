import appdaemon.plugins.hass.hassapi as hass

import auto_switch


class EnabledSwitch(hass.Hass):
    def initialize(self):
        self.mutex = self.get_app('locker').get_mutex('EnabledSwitch')
        self.enabler = self.get_app(self.args['enabler'])
        self.targets = auto_switch.MultiSwitcher(self, self.args['targets'])
        self.enabler_id = self.enabler.add_callback(self.set_state)

        def init_guard(arg):
            name = self.args.get(arg)
            if name is None:
                return (None, None)
            enabler = self.get_app(name)
            enabler_id = enabler.add_callback(self.set_state)
            return (enabler, enabler_id)

        (self.on_guard, self.on_guard_id) = init_guard('on_guard')
        (self.off_guard, self.off_guard_id) = init_guard('off_guard')

        if self.enabler.is_enabled():
            self.run_in(lambda _: self.targets.turn_on(), 0)

    def terminate(self):
        self.enabler.remove_callback(self.enabler_id)
        if self.on_guard is not None:
            self.on_guard.remove_callback(self.on_guard_id)
        if self.off_guard is not None:
            self.off_guard.remove_callback(self.off_guard_id)
        self.targets.turn_off()

    def _is_guard_on(self, guard):
        if guard is None:
            return True
        return guard.is_enabled()

    def set_state(self):
        with self.mutex.lock('set_state'):
            enabled = self.enabler.is_enabled()
            on_guard_on = self._is_guard_on(self.on_guard)
            off_guard_on = self._is_guard_on(self.off_guard)
            self.log('enabled={} on_guard={} off_guard={}'.format(
                enabled, on_guard_on, off_guard_on))
            if enabled:
                if on_guard_on:
                    self.targets.turn_on()
            else:
                if off_guard_on:
                    self.targets.turn_off()
