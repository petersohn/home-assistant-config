import appdaemon.plugins.hass.hassapi as hass


class TemperatureController(hass.Hass):

    def initialize(self):
        self.target = self.args['target']
        self.minimum = float(self.args['minimum'])
        self.tolerance = float(self.args.get('tolerance', 1.0))
        self.low_mode_start = float(
            self.args.get('low_mode_start', 30)) * 60
        self.low_mode_time = float(self.args.get('low_mode_time', 5)) * 60
        self.timer = None
        self.low_mode_limit = None
        self.mutex = self.get_app('locker').get_mutex('TemperatureController')
        self.listen_state(self.trigger, entity=self.args['sensor'])
        self.listen_state(self.trigger, entity=self.args['availability'])

        with self.mutex.lock('initialize'):
            self.__check()

    def trigger(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('trigger'):
            self.__check()

    def __check(self):
        outside_temperature = float(
            self.get_state(self.args['outside_sensor']))
        if type(self.target) is dict:
            min_temperature = float(self.target['min_temperature'])
            max_temperature = float(self.target['max_temperature'])
            min_target = float(self.target['min_target'])
            max_target = float(self.target['max_target'])
            coefficient = (
                (min_target - max_target)
                / (min_temperature - max_temperature))
            constant = min_target - min_temperature * coefficient
            target = coefficient * outside_temperature + constant
            target = min(min_target, max(max_target, target))
        else:
            target = float(self.target)

        temperature = float(self.get_state(self.args['sensor']))

        if temperature > target + self.tolerance:
            self.__stop_timer()
            self.turn_on(self.args['switch'])
        elif temperature < self.minimum:
            self.__stop_timer()
            self.turn_off(self.args['switch'])
        elif temperature < target - self.tolerance:
            if self.low_mode_limit and temperature > self.low_mode_limit:
                self.__stop_timer()
            if self.timer is None:
                self.turn_off(self.args['switch'])
                self.__schedule_start(temperature)

    def __schedule_start(self, current_temperature):
        self.__stop_timer()

        self.log(
                'Start pump if temperature remains below '
                + str(current_temperature) + ' in '
                + str(self.args['low_mode_start']) + ' minutes')
        self.low_mode_limit = current_temperature
        self.timer = self.run_in(
            self.on_start_timer, self.low_mode_start)

    def __schedule_stop(self):
        self.__stop_timer()
        self.log('Schedule low mode stop')
        self.timer = self.run_in(self.on_stop_timer, self.low_mode_time)

    def __stop_timer(self):
        if self.timer is not None:
            self.log('Stop timer')
            self.cancel_timer(self.timer)
            self.timer = None

    def on_start_timer(self, kwargs):
        with self.mutex.lock('on_start_timer'):
            self.log('Low mode start')
            self.turn_on(self.args['switch'])
            self.__schedule_stop()

    def on_stop_timer(self, kwargs):
        with self.mutex.lock('on_stop_timer'):
            self.log('Low mode stop')
            self.turn_off(self.args['switch'])
            self.__schedule_start(float(self.get_state(self.args['sensor'])))
