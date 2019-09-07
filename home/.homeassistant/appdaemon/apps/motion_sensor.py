import appdaemon.plugins.hass.hassapi as hass
import auto_switch


class MotionSensor(hass.Hass):

    def initialize(self):
        self.sensors = self.args['sensors']
        self.targets = auto_switch.MultiSwitcher(self, self.args['targets'])
        self.time = float(self.args['time']) * 60
        enabler = self.args.get('enabler')
        if enabler is not None:
            self.enabler = self.get_app(enabler)
            self.enabler.on_change(self.on_enabled_chaged)
        else:
            self.enabler = None

        self.timer = None
        self.mutex = self.get_app('locker').get_mutex('MotionSensor')

        for sensor in self.sensors:
            self.listen_state(self.on_motion_start, entity=sensor, new='on')
            self.listen_state(self.on_motion_stop, entity=sensor, new='off')

    def on_enabled_chaged(self):
        with self.mutex.lock('on_enabled_chaged'):
            value = self.__should_start()
            self.log('enabled changed to {}'.format(value))
            if value:
                if any([self.get_state(sensor) == 'on'
                        for sensor in self.sensors]):
                    self.__start()
            else:
                self.__stop_timer()
                self.targets.turn_off()

    def on_motion_start(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('on_motion_start'):
            self.log('motion start: {} enabled={}'.format(
                entity, self.__should_start()))
            if self.__should_start():
                self.__start()

    def on_motion_stop(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('on_motion_stop'):
            self.log('motion stop: {}'.format(entity))
            if all(self.get_state(sensor) == 'off' for sensor in self.sensors):
                self.log('Starting timer')
                self.timer = self.run_in(self.on_timeout, self.time)

    def __start(self):
        self.__stop_timer()
        self.targets.turn_on()

    def on_timeout(self, kwargs):
        with self.mutex.lock('on_timeout'):
            self.log('Timeout')
            self.targets.turn_off()

    def __stop_timer(self):
        if self.timer is not None:
            self.cancel_timer(self.timer)
            self.timer = None

    def __should_start(self):
        if self.enabler is None:
            return True
        return self.enabler.is_enabled()
