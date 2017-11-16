import appdaemon.appapi as appapi

import auto_switch

class MotionSensor(appapi.AppDaemon):

    def initialize(self):
        self.__sensors = self.args['sensors']
        self.__targets = [
            auto_switch.AutoSwitch(self, target)
            for target in self.args['targets']]
        self.__time = float(self.args['time']) * 60

        self.__timer = None

        for sensor in self.__sensors:
            self.listen_state(self.__on_motion_start, entity=sensor, new='on')
            self.listen_state(self.__on_motion_stop, entity=sensor, new='off')

    def __on_motion_start(self, entity, attribute, old, new, kwargs):
        self.__stop_timer()
        for target in self.__targets:
            target.turn_on()

    def __on_motion_stop(self, entity, attribute, old, new, kwargs):
        if all([self.get_state(sensor) == 'off' for sensor in self.__sensors]):
            self.log('Starting timer')
            self.__timer = self.run_in(self.__on_timeout, self.__time)

    def __on_timeout(self, kwargs):
        self.log('Timeout')
        for target in self.__targets:
            target.turn_off()

    def __stop_timer(self):
        if self.__timer is not None:
            self.cancel_timer(self.__timer)
            self.__timer = None

