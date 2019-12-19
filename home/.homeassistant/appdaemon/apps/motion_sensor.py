import appdaemon.plugins.hass.hassapi as hass
import auto_switch
import copy


class MotionSensor(hass.Hass):

    def initialize(self):
        self.sensor = self.args['sensor']
        self.targets = auto_switch.MultiSwitcher(self, self.args['targets'])
        self.time = float(self.args['time']) * 60
        enabler = self.args.get('enabler')
        if enabler is not None:
            self.enabler = self.get_app(enabler)
            self.enabler.on_change(self.on_enabled_chaged)
        else:
            self.enabler = None

        self.timer = None
        self.was_enabled = None
        self.mutex = self.get_app('locker').get_mutex('MotionSensor')

        self.listen_state(self.on_motion_start, entity=self.sensor, new='on')
        self.listen_state(self.on_motion_stop, entity=self.sensor, new='off')

    def terminate(self):
        self.targets.turn_off()

    def on_enabled_chaged(self):
        with self.mutex.lock('on_enabled_chaged'):
            value = self.__should_start()
            if self.was_enabled != value:
                self.was_enabled = value
                self.log('enabled changed to {}'.format(value))
                if value:
                    if self.get_state(self.sensor) == 'on':
                        self.__start()
                else:
                    self.__stop_timer()
                    self.targets.turn_off()

    def __handle_start(self, entity):
        # self.log('motion start: {} enabled={} sensor_enabled={}'.format(
        #     entity, self.__should_start(), self.__is_sensor_enabled(entity)))
        if self.__should_start():
            self.__start()

    def on_motion_start(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('on_motion_start'):
            self.__handle_start(entity)

    def __handle_stop(self, entity):
        # self.log('motion stop: {}'.format(entity))
        if self.timer is None:
            self.timer = self.run_in(self.on_timeout, self.time)

    def on_motion_stop(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('on_motion_stop'):
            self.__handle_stop(entity)

    def __start(self):
        self.__stop_timer()
        self.targets.turn_on()

    def on_timeout(self, kwargs):
        with self.mutex.lock('on_timeout'):
            # self.log('Timeout')
            self.targets.turn_off()

    def __stop_timer(self):
        if self.timer is not None:
            self.cancel_timer(self.timer)
            self.timer = None

    def __should_start(self):
        if self.enabler is None:
            return True
        return self.enabler.is_enabled()
