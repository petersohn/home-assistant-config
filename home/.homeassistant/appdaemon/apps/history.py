import appdaemon.plugins.hass.hassapi as hass
import datetime
from urllib import request
import http.client
import json
from collections import namedtuple
import re
import traceback


HistoryElement = namedtuple('HistoryElement', ['time', 'value'])


class HistoryManager(hass.Hass):
    def initialize(self):
        self.max_interval = datetime.timedelta(
            **self.args.get('max_interval', {'days': 1}))
        self.entity_id = self.args['entity']
        self.hass_config = [
            config for config in self.config['plugins'].values()
            if config['type'] == 'hass'][0]
        self.history = []
        self.loaded = False
        self.__load_config()

    def is_loaded(self):
        return self.loaded

    def __make_history_element(self, time, value):
        if value == 'off':
            real_value = 0.0
        elif value == 'on':
            real_value = 1.0
        else:
            real_value = float(value)
        return HistoryElement(time, real_value)

    def _get_limited_history(self, interval):
        limit = self.datetime() - interval
        result = []
        previous = None
        for element in self.history:
            if element.time >= limit:
                if not result and element.time != limit and \
                        previous is not None:
                    result.append(self.__make_history_element(limit, previous))
                result.append(element)
            else:
                previous = element.value
        if not result and previous is not None:
            result.append(self.__make_history_element(limit, previous))
        return result

    def __filter(self):
        if not self.history:
            return
        self.history = self._get_limited_history(self.max_interval)

    def get_history(self, interval=None):
        self.__filter()
        if interval is not None:
            return self._get_limited_history(interval)
        else:
            return self.history

    def __load_config(self, *args, **kwargs):
        self.log('Loading history...')
        try:
            timestamp = (
                datetime.datetime.now() - self.max_interval).strftime(
                '%Y-%m-%dT%H:%M:%S%z')
            url = (self.hass_config['ha_url'] + '/api/history/period/'
                   + timestamp + '?filter_entity_id=' + self.entity_id)
            self.log('Calling API: ' + url)
            with request.urlopen(request.Request(
                    url,
                    headers={
                        'Authorization':
                            'Bearer ' + self.hass_config['token'],
                    })) \
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
                self.history = list(filter(
                    lambda element:
                        element.time <= now and element.value is not None,
                    (self.__make_history_element(
                        get_date(change['last_changed']),
                        change['state'])
                     for changes in loaded_history for change in changes)))
        except:
            self.log('Failed to load history.', level='WARNING')
            self.log(traceback.format_exc(), level='WARNING')
            self.run_in(self.__load_config, 2)
            raise

        self.__filter()
        self.listen_state(
            self.__on_changed, entity=self.entity_id)
        self.loaded = True
        self.log('History loaded.')

    def __on_changed(self, entity, attribute, old, new, kwargs):
        if new == old:
            return
        self.__filter()
        self.history.append(self.__make_history_element(self.datetime(), new))


class AggregatorContext:
    def __init__(self, history, now, base_interval, app):
        self.history = history
        self.now = now
        self.base_interval = base_interval
        self.app = app

    def _get_interval(self, index):
        if index < 0 or index >= len(self.history):
            raise IndexError
        if index == len(self.history) - 1:
            return self.now - self.history[-1].time
        else:
            return self.history[index + 1].time - self.history[index].time

    def _get_normalized(self, index):
        return self.history[index].value * (
            self._get_interval(index) / self.base_interval)

    def integral(self):
        result = 0.0
        for i in range(len(self.history)):
            result += self._get_normalized(i)
        return result

    def mean(self):
        if not self.history:
            return 0.0
        total_time = (self.now - self.history[0].time) / self.base_interval
        if total_time == 0.0:
            return 0.0
        return self.integral() / total_time

    def anglemean(self):
        if not self.history:
            return 0.0
        self.app.log('history={}'.format(self.history))
        if self.now == self.history[0].time:
            return self.history[0].value % 360
        total_time = (self.now - self.history[0].time) / self.base_interval

        Normalized = namedtuple('Normalized', ['time', 'value360', 'value180'])
        normalized = [
            Normalized(
                self._get_interval(i) / self.base_interval,
                self.history[i].value % 360,
                self.history[i].value - 360
                if self.history[i].value >= 180
                else self.history[i].value)
            for i in range(len(self.history))]

        mean360 = sum(x.value360 * x.time for x in normalized) / total_time
        mean180 = sum(x.value180 * x.time for x in normalized) / total_time
        variance360 = sum(
            (x.value360 - mean360) * (x.value360 - mean360) * x.time
            for x in normalized)
        variance180 = sum(
            (x.value180 - mean180) * (x.value180 - mean180) * x.time
            for x in normalized)

        if variance180 < variance360:
            if mean180 < 0:
                mean180 += 360
            return mean180
        else:
            return mean360

    def min(self):
        if self.history:
            return min(e.value for e in self.history)
        return 0

    def max(self):
        if self.history:
            return max(e.value for e in self.history)
        return 0

    def sum(self):
        return sum(e.value for e in self.history)

    def get_functions(self):
        return {
            'integral': self.integral,
            'mean': self.mean,
            'anglemean': self.anglemean,
            'min': self.min,
            'max': self.max,
            'sum': self.sum,
        }


class Aggregator:
    def __init__(self, app, callback):
        self.app = app
        self.manager = app.get_app(app.args['manager'])
        self.expr = app.args['aggregator']
        self.base_interval = datetime.timedelta(
            **app.args.get('base_interval', {'minutes': 1}))
        if 'interval' in app.args:
            self.interval = datetime.timedelta(**app.args['interval'])
        else:
            self.interval = None
        self.callback = callback
        self.__start_timer()
        app.listen_state(self.__on_change, self.manager.entity_id)
        self.__set_state()

    def __set_state(self):
        history = self.manager.get_history(self.interval)
        context = AggregatorContext(
            history, self.manager.datetime(), self.base_interval, self.app)
        func = eval(self.expr, {}, context.get_functions())
        value = func()
        self.callback(value)

    def __start_timer(self):
        self.timer = self.app.run_every(
            self.__on_interval,
            self.app.datetime() + self.base_interval,
            self.base_interval.total_seconds())

    def __on_change(self, entity, attribute, old, new, kwargs):
        self.app.cancel_timer(self.timer)
        self.__set_state()
        self.__start_timer()

    def __on_interval(self, kwargs):
        self.__set_state()


class AggregatedValue(hass.Hass):
    def initialize(self):
        self.target = self.args['target']
        self.attributes = self.args.get('attributes', {})
        self.aggregator_app = Aggregator(self, self.__set_state)

    def __set_state(self, value):
        self.set_state(self.target, state=value, attributes=self.attributes)
