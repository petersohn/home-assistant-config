import appdaemon.appapi as appapi


class TemperatureController(appapi.AppDaemon):

    def initialize(self):
        self.__target = float(self.args['target'])
        self.__tolerance = float(self.args.get('tolerance', 1.0))
        self.listen_state(self.trigger, entity=self.args['sensor'])
        self.listen_state(self.trigger, entity=self.args['availability'])
        self.__check()

    def trigger(self, entity, attribute, old, new, kwargs):
        self.__check()

    def __check(self):
        temperature = float(self.get_state(self.args['sensor']))

        if temperature < self.__target - self.__tolerance:
            self.turn_off(self.args['switch'])
        elif temperature > self.__target + self.__tolerance:
            self.turn_on(self.args['switch'])
