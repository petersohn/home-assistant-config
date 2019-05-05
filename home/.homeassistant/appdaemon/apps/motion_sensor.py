import appdaemon.plugins.hass.hassapi as hass

import auto_switch


class MotionSensor(hass.Hass):

    def initialize(self):
        self.__sensors = self.args['sensors']
        self.__targets = auto_switch.MultiSwitcher(self, self.args['targets'])
        self.__time = float(self.args['time']) * 60
        enabler = self.args.get('enabler')
        if enabler is not None:
            self.__enabler = self.get_app(enabler)
            self.__enabler.on_change(self.__on_enabled_chaged)
        else:
            self.__enabler = None

        self.__timer = None

        for sensor in self.__sensors:
            self.listen_state(self.__on_motion_start, entity=sensor, new='on')
            self.listen_state(self.__on_motion_stop, entity=sensor, new='off')

    def __on_enabled_chaged(self, value):
        if value:
            if any([self.get_state(sensor) == 'on'
                    for sensor in self.__sensors]):
                self.__start()
        else:
            self.__stop_timer()
            self.__targets.turn_off()

    def __on_motion_start(self, entity, attribute, old, new, kwargs):
        self.log(
            'motion start: ' + entity
            + ' enabled=' + str(self.__should_start()))
        if self.__should_start():
            self.__start()

    def __on_motion_stop(self, entity, attribute, old, new, kwargs):
        if all([self.get_state(sensor) == 'off' for sensor in self.__sensors]):
            self.log('Starting timer')
            self.__timer = self.run_in(self.__on_timeout, self.__time)

    def __start(self):
        self.__stop_timer()
        self.__targets.turn_on()

    def __on_timeout(self, kwargs):
        self.log('Timeout')
        self.__targets.turn_off()

    def __stop_timer(self):
        if self.__timer is not None:
            self.cancel_timer(self.__timer)
            self.__timer = None

    def __should_start(self):
        if self.__enabler is None:
            return True
        return self.__enabler.is_enabled()
