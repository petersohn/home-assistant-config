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
        self.refresh_interval = None
        if 'refresh_interval' in self.args:
            self.refresh_interval = datetime.timedelta(
                **self.args['refresh_interval'])
        self.__hass_config = [
            config for config in self.config['plugins'].values()
            if config['type'] == 'hass'][0]
        self.__history = []
        self.__loaded = False
        self.__load_config()

    def is_loaded(self):
        return self.__loaded

    def __fill(self):
        if not self.__history:
            return

        if self.refresh_interval is not None:
            limit = self.datetime() - self.refresh_interval
            while self.__history[-1].time < limit:
                value = self.__history[-1].value
                # self.log('+' + str(value))
                self.__history.append(HistoryElement(
                    self.__history[-1].time + self.refresh_interval,
                    value))

        limit = self.datetime() - self.max_interval
        self.__history = list(filter(
            lambda element: element.time >= limit, self.__history))

    def get_history(self, interval=None):
        self.__fill()
        if interval is not None:
            limit = self.datetime() - interval
            return [
                element for element in self.__history if element.time > limit]
        else:
            return self.__history

    def get_values(self, interval=None):
        return [element.value for element in self.get_history(interval)]

    def __load_config(self, *args, **kwargs):
        self.log('Loading history...')
        try:
            timestamp = (
                datetime.datetime.now() - self.max_interval).strftime(
                '%Y-%m-%dT%H:%M:%S%z')
            url = (self.__hass_config['ha_url'] + '/api/history/period/'
                   + timestamp + '?filter_entity_id=' + self.entity_id)
            self.log('Calling API: ' + url)
            with request.urlopen(request.Request(
                    url,
                    headers={
                        'Authorization':
                            'Bearer ' + self.__hass_config['token'],
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
                self.__history = list(filter(
                    lambda element: element.time <= now,
                    (HistoryElement(
                        get_date(change['last_changed']),
                        change['state'])
                     for changes in loaded_history for change in changes)))
        except:
            self.log('Failed to load history.', level='WARNING')
            self.log(traceback.format_exc(), level='WARNING')
            self.run_in(self.__load_config, 2)
            raise

        self.__fill()
        self.listen_state(
            self.__on_changed, entity=self.entity_id)
        self.__loaded = True
        self.log('History loaded.')

    def __on_changed(self, entity, attribute, old, new, kwargs):
        if new == old:
            return
        self.__fill()
        self.__history.append(HistoryElement(self.datetime(), new))


class Aggregator:
    def __init__(self, manager, expr, default):
        import aggregator
        self.__manager = manager
        self.__aggregator = eval(expr, aggregator.__dict__, {})
        self.__default = default

    def get(self, interval):
        values = []
        raw = self.__manager.get_values(interval)
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

        result = self.__aggregator(values)
        return result


class AggregatorApp:
    def __init__(self, app, callback):
        self.__app = app
        self.__manager = app.get_app(app.args['manager'])
        self.__aggregator = Aggregator(
            self.__manager,
            app.args['aggregator'],
            app.args.get('default'))
        if 'interval' in app.args:
            self.__interval = datetime.timedelta(**app.args['interval'])
        else:
            self.__interval = None
        self.__callback = callback
        if self.__manager.refresh_interval is not None:
            app.run_every(
                lambda _: self.__set_state(), self.__app.datetime(),
                self.__manager.refresh_interval.seconds)
        else:
            app.listen_state(self.__on_change, self.__manager.entity_id)
        self.__timer_needed = self.__interval is not None and \
            self.__manager.refresh_interval is None
        self.__timer = None
        self.__set_state()

    def __set_state(self):
        if self.__timer is not None:
            self.__app.cancel_timer(self.__timer)
            self.__timer = None
        value = self.__aggregator.get(self.__interval)
        self.__callback(value)
        if self.__timer_needed:
            history = self.__manager.get_history(self.__interval)
            if history:
                next_run = history[0].time + self.__interval
                if next_run > self.__app.datetime():
                    self.__timer = self.__app.run_at(
                        lambda _: self.__set_state(), next_run)

    def __on_change(self, entity, attribute, old, new, kwargs):
        if old != new:
            self.__set_state()


class AggregatedValue(hass.Hass):
    def initialize(self):
        self.__target = self.args['target']
        self.attributes = self.args.get('attributes', {})
        self.__aggregator_app = AggregatorApp(self, self.__set_state)

    def __set_state(self, value):
        self.set_state(
            self.__target, state=value, attributes=self.attributes)
