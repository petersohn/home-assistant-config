import appdaemon.plugins.hass.hassapi as hass
import datetime
from urllib import request
import http.client
import json
from collections import namedtuple
import re
import pprint


HistoryElement = namedtuple('HistoryElement', ['time', 'value'])


class HistoryManager(hass.Hass):
    def initialize(self):
        self.__max_interval = datetime.timedelta(**self.args['max_interval'])
        self.__entity_id = self.args['entity']
        self.__hass_config = [
            config for config in self.config['plugins'].values()
            if config['type'] == 'hass'][0]
        self.__history = []
        self.__loaded = False
        self.__load_config()

    def is_loaded(self):
        return self.__loaded

    def get_history(self, interval=None):
        self.log('interval=%s' % interval)
        if interval is not None:
            limit = self.datetime() - interval
            self.log('limit=%s' % limit)
            return [
                element for element in self.__history if element.time >= limit]
        else:
            self.log('no limit')
            return self.__history

    def get_values(self, interval=None):
        return [element.value for element in self.get_history(interval)]

    def __load_config(self):
        self.log('Loading history...')
        try:
            timestamp = (
                datetime.datetime.now() - self.__max_interval).strftime(
                '%Y-%m-%dT%H:%M:%S%z')
            url = (self.__hass_config['ha_url'] + '/api/history/period/'
                   + timestamp + '?filter_entity_id=' + self.__entity_id)
            self.log('Calling API: ' + url)
            with request.urlopen(request.Request(
                    url,
                    headers={'x-ha-access': self.__hass_config['ha_key']})) \
                    as result:
                if result.status >= 300:
                    raise http.client.HTTPException(result.reason)
                loaded_history = json.load(result)
                self.log('history=%s' % pprint.pformat(loaded_history))
                self.__history = [
                    HistoryElement(
                        datetime.datetime.strptime(
                            re.sub(
                                r'([-+][0-9]{2}):([0-9]{2})$', '',
                                change['last_changed']),
                            '%Y-%m-%dT%H:%M:%S.%f'),
                        change['state'])
                    for changes in loaded_history for change in changes]
        except:
            self.log('Failed to load history.', level='WARNING')
            self.run_in(self.__load_config, 2)
            raise

        self.listen_state(
            self.__on_changed, entity=self.__entity_id)
        self.__loaded = True
        self.log('History loaded.')

    def __on_changed(self, entity, attribute, old, new, kwargs):
        now = self.datetime()
        limit = now - self.__max_interval
        self.__history = list(filter(
            lambda element: element.time >= limit, self.__history))
        self.__history.append(HistoryElement(now, new))
