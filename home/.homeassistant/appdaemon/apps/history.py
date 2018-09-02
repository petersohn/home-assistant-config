import appdaemon.plugins.hass.hassapi as hass
import datetime
from urllib import request
import http.client
import json
from collections import namedtuple
import re
import pprint
import traceback


HistoryElement = namedtuple('HistoryElement', ['time', 'value'])


class HistoryManager(hass.Hass):
    def initialize(self):
        self.__max_interval = datetime.timedelta(
            **self.args.get('max_interval', {'days': 1}))
        self.entity_id = self.args['entity']
        self.__hass_config = [
            config for config in self.config['plugins'].values()
            if config['type'] == 'hass'][0]
        self.__history = []
        self.__loaded = False
        self.__load_config()

    def is_loaded(self):
        return self.__loaded

    def get_history(self, interval=None):
        if interval is not None:
            limit = self.datetime() - interval
            # self.log(pprint.pformat(['{}: {}'.format(e.time, e.value) for e in self.__history]))
            return [
                element for element in self.__history if element.time > limit]
        else:
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
                   + timestamp + '?filter_entity_id=' + self.entity_id)
            self.log('Calling API: ' + url)
            with request.urlopen(request.Request(
                    url,
                    headers={'x-ha-access': self.__hass_config['ha_key']})) \
                    as result:
                if result.status >= 300:
                    raise http.client.HTTPException(result.reason)
                loaded_history = json.loads(result.read().decode())

                def get_date(s):
                    s = re.sub(r'([-+][0-9]{2}):([0-9]{2})$', '', s)
                    try:
                        return datetime.datetime.strptime(
                            s, '%Y-%m-%dT%H:%M:%S.%f')
                    except ValueError:
                        return datetime.datetime.strptime(
                            s, '%Y-%m-%dT%H:%M:%S')

                now = self.datetime()
                self.__history = list(filter(
                    lambda element: element.time <= now,
                    (HistoryElement(
                        get_date(change['last_changed']),
                        change['state'])
                     for changes in loaded_history for change in changes)))
                self.log('History size={}'.format(len(self.__history)))
        except:
            self.log('Failed to load history.', level='WARNING')
            self.log(traceback.format_exc(), level='WARNING')
            self.run_in(self.__load_config, 2)
            raise

        self.listen_state(
            self.__on_changed, entity=self.entity_id)
        self.__loaded = True
        self.log('History loaded.')

    def __on_changed(self, entity, attribute, old, new, kwargs):
        now = self.datetime()
        limit = now - self.__max_interval
        self.__history = list(filter(
            lambda element: element.time >= limit, self.__history))
        self.__history.append(HistoryElement(now, new))


class Aggregator:
    def __init__(self, manager, expr, default):
        import aggregator
        self.__manager = manager
        self.__aggregator = eval(expr, aggregator.__dict__, {})
        self.__default = default

    def get(self, interval):
        values = []
        raw = self.__manager.get_values(interval)
        # self.__manager.log('raw={}'.format(raw))
        for value in raw:
            try:
                values.append(float(value))
            except ValueError:
                pass
        if not values:
            if self.__default is not None:
                values = [self.__default]
            else:
                values = self.__manager.get_values()[-1:]
        # self.__manager.log('values={}'.format(values))
        result = self.__aggregator(values)
        # self.__manager.log('result={}'.format(result))
        return result


class AggregatedValue(hass.Hass):
    def initialize(self):
        manager = self.get_app(self.args['manager'])
        self.__aggregator = Aggregator(
            manager,
            self.args['aggregator'],
            self.args.get('default'))
        self.__target = self.args['target']
        self.__interval = datetime.timedelta(**self.args['interval'])
        self.listen_state(self.__on_change, manager.entity_id)
        self.__set_state()

    def __set_state(self):
        value = self.__aggregator.get(self.__interval)
        self.set_state(
            self.__target, state=value)

    def __on_change(self, entity, attribute, old, new, kwargs):
        self.__set_state()
