import appdaemon.plugins.hass.hassapi as hass
import auto_switch
import traceback


class MotionSensor(hass.Hass):

    def initialize(self):
        self.sensor = self.args['sensor']
        self.targets = auto_switch.MultiSwitcher(self, self.args['targets'])
        try:
            self.time = float(self.args['time']) * 60
        except ValueError:
            self.time = self.args['time']
        self.edge_trigger = self.args.get('edge_trigger', False)
        self.target_state = self.args.get('target_state', 'on')
        enabler = self.args.get('enabler')
        if enabler is not None:
            self.enabler = self.get_app(enabler)
            self.enabler_id = self.enabler.on_change(self.on_enabled_chaged)
        else:
            self.enabler = None
            self.enabler_id = None

        self.timer = None
        self.was_enabled = None
        self.mutex = self.get_app('locker').get_mutex('MotionSensor')

        self.listen_state(self.on_state_change, entity=self.sensor)

    def terminate(self):
        self.targets.turn_off()
        self.enabler.remove_callback(self.enabler_id)

    def on_enabled_chaged(self):
        with self.mutex.lock('on_enabled_chaged'):
            enabled = self.__should_start()
            if self.was_enabled != enabled:
                self.was_enabled = enabled
                self.log('enabled changed to {}'.format(enabled))
                if enabled:
                    if not self.edge_trigger and \
                            self.get_state(self.sensor) == self.target_state:
                        self.__start()
                else:
                    self.__stop_timer()
                    self.targets.turn_off()

    def __handle_start(self):
        if self.__should_start():
            self.__start()

    def on_state_change(self, entity, attribute, old, new, kwargs):
        # self.log('state changed: {} -> {} target={}'.format(
        #     old, new, self.target_state))
        with self.mutex.lock('on_state_change'):
            if old == new:
                # This shouldn't happen, but just in case.
                return
            if new == self.target_state:
                self.__handle_start()
                if self.edge_trigger:
                    self.__handle_stop()
            elif not self.edge_trigger and old == self.target_state:
                self.__handle_stop()

    def __handle_stop(self):
        if self.timer is None:
            if type(self.time) is float:
                time = self.time
            else:
                try:
                    time = float(self.get_state(self.time)) * 60
                except Exception:
                    self.error(traceback.format_exc())
                    time = 0
            self.timer = self.run_in(self.on_timeout, time)

    def __start(self):
        self.__stop_timer()
        self.log('Turn on')
        self.targets.turn_on()

    def on_timeout(self, kwargs):
        with self.mutex.lock('on_timeout'):
            self.log('Turn off')
            self.targets.turn_off()

    def __stop_timer(self):
        if self.timer is not None:
            self.cancel_timer(self.timer)
            self.timer = None

    def __should_start(self):
        if self.enabler is None:
            return True
        return self.enabler.is_enabled()
