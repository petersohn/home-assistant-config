import appdaemon.appapi as appapi


class WindDirection(appapi.AppDaemon):

    _DIRECTIONS = [
        'mdi:arrow-down', 'mdi:arrow-bottom-left', 'mdi:arrow-left',
        'mdi:arrow-top-left', 'mdi:arrow-up', 'mdi:arrow-top-right',
        'mdi:arrow-right', 'mdi:arrow-bottom-right']

    _NUM_DIRECTIONS = len(_DIRECTIONS)
    _DIRECTION_DIVISOR = 360.0 / _NUM_DIRECTIONS
    _DIRECTION_OFFSET = _DIRECTION_DIVISOR / 2.0

    _ENTITY_NAME = 'sensor.yr_wind_direction'

    def initialize(self):
        self.listen_state(
            self.on_wind_changed, entity=self._ENTITY_NAME)
        self.__set_wind_direction_icon()
        self.log('Initialized wind direction checker')

    def on_wind_changed(self, entity, attribute, old, new, kwargs):
        self.__set_wind_direction_icon()

    def __set_wind_direction_icon(self):
        self.log("Setting wind direction icon")
        wind_direction = self.get_state(self._ENTITY_NAME, 'all')
        wind_direction['attributes']['icon'] = self._DIRECTIONS[int(
            (float(wind_direction['state']) + self._DIRECTION_OFFSET)
            / self._DIRECTION_DIVISOR) % self._NUM_DIRECTIONS]

        self.set_state(
            self._ENTITY_NAME, attributes=wind_direction['attributes'])
