import appdaemon.plugins.hass.hassapi as hass
import auto_switch
import copy


class MotionSensor(hass.Hass):

    def initialize(self):
        enabled_sensors = self.args.get('enabled_sensors', {})
        self.sensors = self.args.get('sensors', [])
        self.sensors.extend(enabled_sensors.keys())
        self.sensors = list(set(self.sensors))
        self.sensor_enablers = {
            k: self.get_app(v) for k, v in enabled_sensors.items()}
        self.targets = auto_switch.MultiSwitcher(self, self.args['targets'])
        self.time = float(self.args['time']) * 60
        enabler = self.args.get('enabler')
        if enabler is not None:
            self.enabler = self.get_app(enabler)
            self.enabler.on_change(self.on_enabled_chaged)
        else:
            self.enabler = None

        def stupid_python_workaround(sensor):
            return lambda: self.on_sensor_enabled_changed(sensor)

        for sensor, enabler in self.sensor_enablers.items():
            enabler.on_change(stupid_python_workaround(sensor))
            enabler._motion_sensor_was_enabled = enabler.is_enabled()

        self.timer = None
        self.was_enabled = None
        self.mutex = self.get_app('locker').get_mutex('MotionSensor')

        for sensor in self.sensors:
            self.listen_state(self.on_motion_start, entity=sensor, new='on')
            self.listen_state(self.on_motion_stop, entity=sensor, new='off')

    def on_sensor_enabled_changed(self, sensor):
        with self.mutex.lock('on_sensor_enabled_changed'):
            enabler = self.sensor_enablers[sensor]
            value = enabler.is_enabled()
            if enabler._motion_sensor_was_enabled != value:
                self.log('sensor enabled changed: {}: {}'.format(
                    sensor, value))
                enabler._motion_sensor_was_enabled = value
                if value:
                    self.__handle_start(sensor)
                else:
                    self.__handle_stop(sensor)

    def on_enabled_chaged(self):
        with self.mutex.lock('on_enabled_chaged'):
            value = self.__should_start()
            if self.was_enabled != value:
                self.was_enabled = value
                self.log('enabled changed to {}'.format(value))
                if value:
                    if any([self.get_state(sensor) == 'on'
                            for sensor in self.sensors]):
                        self.__start()
                else:
                    self.__stop_timer()
                    self.targets.turn_off()

    def __is_sensor_enabled(self, sensor):
        if sensor not in self.sensor_enablers:
            return True
        return self.sensor_enablers[sensor].is_enabled()

    def __handle_start(self, entity):
        # self.log('motion start: {} enabled={} sensor_enabled={}'.format(
        #     entity, self.__should_start(), self.__is_sensor_enabled(entity)))
        if self.__should_start() and self.__is_sensor_enabled(entity):
            self.__start()

    def on_motion_start(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('on_motion_start'):
            self.__handle_start(entity)

    def __handle_stop(self, entity):
        # self.log('motion stop: {}'.format(entity))
        if all(not self.__is_sensor_enabled(sensor)
               or self.get_state(sensor) == 'off'
               for sensor in self.sensors):
            # self.log('Starting timer')
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
