import appdaemon.plugins.hass.hassapi as hass


class TemperatureBasic(hass.Hass):
    def initialize(self):
        self.sensor_in = self.args['sensor_in']
        self.sensor_out = self.args['sensor_out']
        self.target = self.args['target']
        self.minimum_out = float(self.args['minimum_out'])
        self.maximum_out = float(self.args['maximum_out'])
        self.target_difference = float(self.args['target_difference'])
        self.tolerance = float(self.args.get('tolerance', '1'))
        self.mutex = self.get_app('locker').get_mutex('TemperatureBasic')

        self.listen_state(self.on_change, self.sensor_in)
        self.listen_state(self.on_change, self.sensor_out)

    def __get_value(self):
        value_out = float(self.get_state(self.sensor_out))
        if value_out < self.minimum_out:
            return False
        if value_out >= self.maximum_out:
            return True
        value_in = float(self.get_state(self.sensor_in))
        diff = value_out - value_in
        current_value = self.get_state(self.target)
        if current_value == 'on':
            return diff >= self.target_difference - self.tolerance
        else:
            return diff >= self.target_difference + self.tolerance

    def on_change(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('on_change'):
            if self.__get_value():
                self.log('on')
                self.turn_on(self.target)
            else:
                self.log('off')
                self.turn_off(self.target)
