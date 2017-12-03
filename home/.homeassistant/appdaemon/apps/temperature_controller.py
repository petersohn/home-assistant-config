import appdaemon.appapi as appapi


class TemperatureController(appapi.AppDaemon):

    def initialize(self):
        self.__target = self.args['target']
        self.__minimum = float(self.args['minimum'])
        self.__tolerance = float(self.args.get('tolerance', 1.0))
        self.__low_mode_start = float(
            self.args.get('low_mode_start', 30)) * 60
        self.__low_mode_time = float(self.args.get('low_mode_time', 5)) * 60
        self.__timer = None
        self.__low_mode_limit = None
        self.listen_state(self.trigger, entity=self.args['sensor'])
        self.listen_state(self.trigger, entity=self.args['availability'])

        self.__check()

    def trigger(self, entity, attribute, old, new, kwargs):
        self.__check()

    def __check(self):
        outside_temperature = float(self.get_state(self.args['outside_sensor']))
        if type(self.__target) is dict:
            min_temperature = float(self.__target['min_temperature'])
            max_temperature = float(self.__target['max_temperature'])
            min_target = float(self.__target['min_target'])
            max_target = float(self.__target['max_target'])
            coefficient = ((min_target - max_target)
                    / (min_temperature - max_temperature))
            constant = min_target - min_temperature * coefficient
            target = coefficient * outside_temperature + constant
            target = min(min_target, max(max_target, target))
        else:
            target = float(self.__target)

        self.log('Target temperature = ' + str(target))
        temperature = float(self.get_state(self.args['sensor']))

        if temperature > target + self.__tolerance:
            self.__stop_timer()
            self.turn_on(self.args['switch'])
        elif temperature < self.__minimum:
            self.__stop_timer()
            self.turn_off(self.args['switch'])
        elif temperature < target - self.__tolerance:
            if self.__low_mode_limit and temperature > self.__low_mode_limit:
                self.__stop_timer()
            if self.__timer is None:
                self.turn_off(self.args['switch'])
                self.__schedule_start(temperature)

    def __schedule_start(self, current_temperature):
        self.__stop_timer()

        self.log(
                'Start pump if temperature remains below '
                + str(current_temperature) + ' in '
                + str(self.args['low_mode_start']) + ' minutes')
        self.__low_mode_limit = current_temperature
        self.__timer = self.run_in(
            self.__on_start_timer, self.__low_mode_start)

    def __schedule_stop(self):
        self.__stop_timer()
        self.log('Schedule low mode stop')
        self.__timer = self.run_in(self.__on_stop_timer, self.__low_mode_time)

    def __stop_timer(self):
        if self.__timer is not None:
            self.log('Stop timer')
            self.cancel_timer(self.__timer)
            self.__timer = None

    def __on_start_timer(self, kwargs):
        self.log('Low mode start')
        self.turn_on(self.args['switch'])
        self.__schedule_stop()

    def __on_stop_timer(self, kwargs):
        self.log('Low mode stop')
        self.turn_off(self.args['switch'])
        self.__schedule_start(float(self.get_state(self.args['sensor'])))
