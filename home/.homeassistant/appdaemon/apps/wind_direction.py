import hass

class WindDirection(hass.Hass):

    _DIRECTIONS = [
        'mdi:arrow-down', 'mdi:arrow-bottom-left', 'mdi:arrow-left',
        'mdi:arrow-top-left', 'mdi:arrow-up', 'mdi:arrow-top-right',
        'mdi:arrow-right', 'mdi:arrow-bottom-right']

    _NUM_DIRECTIONS = len(_DIRECTIONS)
    _DIRECTION_DIVISOR = 360.0 / _NUM_DIRECTIONS
    _DIRECTION_OFFSET = _DIRECTION_DIVISOR / 2.0

    def initialize(self):
        self.__entity_name = self.args['entity']
        self.listen_state(
            self.on_wind_changed, entity=self.__entity_name)
        self.__set_wind_direction_icon()

    def on_wind_changed(self, entity, attribute, old, new, kwargs):
        self.__set_wind_direction_icon()

    def __set_wind_direction_icon(self):
        wind_direction = self.get_state(
            entity=self.__entity_name, attribute='all')
        if wind_direction is None:
            self.log('No wind direction.')
            return
        try:
            wind_direction['attributes']['icon'] = self._DIRECTIONS[int(
                (float(wind_direction['state']) + self._DIRECTION_OFFSET)
                / self._DIRECTION_DIVISOR) % self._NUM_DIRECTIONS]
        except ValueError:
            self.log('Wind direction is invalid: ' + wind_direction['state'])
            return

        self.set_state(
            self.__entity_name, attributes=wind_direction['attributes'])
