import appdaemon.plugins.hass.hassapi as hass
import datetime
from dateutil import tz
from urllib import request
import http.client
import json
import math
from collections import namedtuple, deque
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
        self.mutex = self.get_app('locker').get_mutex('HistoryManager')
        self.load_config()

    def is_loaded(self):
        return self.loaded

    def __make_history_element(self, time, value):
        try:
            if value == 'off':
                real_value = 0.0
            elif value == 'on':
                real_value = 1.0
            else:
                real_value = float(value)
        except ValueError:
            real_value = 0.0
        return HistoryElement(time, real_value)

    def __filter(self):
        while len(self.history) >= 2 and self.history[1].time < self.datetime():
            self.history.popleft()

    def get_history(self):
        with self.mutex.lock('get_history'):
            self.__filter()
            return self.history

    def load_config(self, *args, **kwargs):
        with self.mutex.lock('load_config'):
            self.log('Loading history...')
            try:
                now = datetime.datetime.now()
                begin_timestamp = (
                    now - self.max_interval).strftime(
                        '%Y-%m-%dT%H:%M:%S')
                end_timestamp = now.strftime('%Y-%m-%dT%H:%M:%S')
                url = '{}/api/history/period/{}?filter_entity_id={}&end_time={}' \
                    .format(
                        self.hass_config['ha_url'],
                        begin_timestamp,
                        self.entity_id,
                        end_timestamp)
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
                    x = result.read().decode()
                    loaded_history = json.loads(x)

                    def get_date(s):
                        s = re.sub(r'([-+][0-9]{2}):([0-9]{2})$', '', s)
                        try:
                            time = datetime.datetime.strptime(
                                s, '%Y-%m-%dT%H:%M:%S.%f')
                        except ValueError:
                            time = datetime.datetime.strptime(
                                s, '%Y-%m-%dT%H:%M:%S')
                        return time.replace(tzinfo=tz.tzutc()). \
                            astimezone(tz.tzlocal()).replace(tzinfo=None)

                    now = self.datetime()
                    self.history = deque(filter(
                        lambda element:
                            element.time <= now and element.value is not None,
                        (self.__make_history_element(
                            get_date(change['last_changed']),
                            change['state'])
                         for changes in loaded_history for change in changes)))
            except:
                self.error('Failed to load history.', level='WARNING')
                self.error(traceback.format_exc(), level='WARNING')
                self.run_in(self.load_config, 2)
                raise

            self.__filter()
            self.listen_state(
                self.on_changed, entity=self.entity_id)
            self.loaded = True
            self.log('History loaded.')

    def on_changed(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('on_changed'):
            if new == old:
                return
            self.__filter()
            self.history.append(self.__make_history_element(
                self.datetime(), self.get_state(self.entity_id)))


class AggregatorContext:
    def __init__(self, history, now, base_interval, app):
        # app.log('history={} now={}'.format(history, now))
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

    def decay_sum(self, fraction, **kwargs):
        interval = datetime.timedelta(**kwargs).total_seconds()

        def get_value(e):
            diff = (self.now - e.time).total_seconds()
            quotient = fraction ** (diff / interval)
            result = e.value * quotient
            return result

        return lambda: sum(get_value(e) for e in self.history)

    def get_functions(self):
        return {
            'integral': self.integral,
            'mean': self.mean,
            'anglemean': self.anglemean,
            'min': self.min,
            'max': self.max,
            'sum': self.sum,
            'decay_sum': self.decay_sum,
        }


class LimitedHistoryAggregatum:
    def __init__(self, interval):
        self.interval = interval
        self.history = deque()

    def add(self, element):
        self.adding(element)
        self.elements.append(element)
        minimum_time = element.time - self.interval
        while len(self.elements) >= 2 and self.elements[1].time < minimum_time:
            removed_element = self.elements.popleft()
            self.removed(removed_element)
        if self.elements[0].time < minimum_time:
            old_element = self.elements[0]
            self.elements[0] = HistoryElement(
                minimum_time, self.elements[0].value)
            self.trimmed(old_element)

    def adding(self, element):
        pass

    def removed(self, element):
        pass

    def trimmed(self, element):
        pass

    def get(self):
        raise NotImplemented


class MinmaxAggregatum(LimitedHistoryAggregatum):
    def __init__(self, interval, function):
        super(MinmaxAggregatum, self).__init__(interval)
        self.value = None
        self.function = function

    def adding(self, element):
        if self.value is None:
            if self.history:
                self._reevaluate()
            else:
                self.value = element.value
        self.value = self.function(self.value, element.value)

    def removed(self, element):
        if math.abs(element.value - self.value) < 0.0001:
            self._reevaluate()

    def _reevaluate(self):
        self.value = self.function(e.value for e in self.history)

    def get(self):
        if self.value is None:
            raise ValueError
        return self.value

def Sum(LimitedHistoryAggregatum):
    def __init__(self, interval):
        super(Sum, self).__init__(interval)
        self.value = 0.0

    def adding(self, element):
        self.value += element.value

    def removed(self, element):
        self.value -= element.value

    def get(self):
        return self.value


class IntervalAggragatum(LimitedHistoryAggregatum):
    def __init__(self, interval):
        super(IntervalAggragatum, self).__init__(interval)

    def adding(self, element):
        if self.history:
            interval = element.time - self.history[-1].time
            self.add_interval(interval, self.history[-1].value)

    def removed(self, element):
        self._remove(element)

    def trimmed(self, element):
        self._remove(element)

    def _remove(self, element):
        interval = self.history[0].time - element.time
        self.remove_interval(interval, element.value)

    def add_interval(self, interval, value):
        raise NotImplemented

    def remove_interval(self, interval, value):
        raise NotImplemented


class Mean(IntervalAggragatum):
    def __init__(self, interval):
        super(Mean, self).__init__(interval)
        self.sum = 0.0
        self.time = 0.0

    def get(self):
        if self.time == 0.0:
            raise ValueError
        return self.sum / self.time

    def add_interval(self, interval, value):
        seconds = interval.total_seconds()
        self.sum += value * seconds
        self.time += seconds

    def remove_interval(self, interval, value):
        seconds = interval.total_seconds()
        self.sum -= value * seconds
        self.time -= seconds


class Anglemean(IntervalAggragatum):
    def __init__(self, interval):
        super(Mean, self).__init__(interval)
        self.sum180 = 0.0
        self.sum360 = 0.0
        self.sum360_2 = 0.0
        self.sum180_2 = 0.0
        self.time = 0.0

    def get(self):
        if self.time == 0.0:
            raise ValueError
        varsum180 = self.sum180 - (self.sum180_2 ** 2) / self.time
        varsum360 = self.sum360 - (self.sum360_2 ** 2) / self.time
        if self.varsum180 < self.sum180:
            return self.sum180 / self.time
        else:
            return self.sum360 / self.time

    def add_interval(self, interval, value):
        value360 = value % 360  # this should be < 360 anyway
        value180 = value - 360 if value > 180 else value
        seconds = interval.total_seconds()
        self.sum180 += value180 * seconds
        self.sum180_2 += (value180 ** 2) * seconds
        self.sum360 += value360 * seconds
        self.sum360_2 += (value360 ** 2) * seconds
        self.time += seconds

    def remove_interval(self, interval, value):
        value360 = value % 360  # this should be < 360 anyway
        value180 = value - 360 if value > 180 else value
        seconds = interval.total_seconds()
        self.sum180 -= value180 * seconds
        self.sum180_2 -= (value180 ** 2) * seconds
        self.sum360 -= value360 * seconds
        self.sum360_2 -= (value360 ** 2) * seconds
        self.time -= seconds


def DecaySum:
    def init(self, interval, fraction):
        self.interval = interval.total_seconds()
        self.fraction = fraction
        self.value = None
        self.time = None

    def add(self, element):
        if self.time is None:
            self.time = element.time
            self.value = element.value
            return

        diff = (element.time - self.time).total_seconds()
        self.value *= fraction ** (diff / self.interval)
        self.value += element.value
        self.time = element.time

    def get(self):
        return self.value


class Aggregator:
    def __init__(self, app, callback):
        self.mutex = app.get_app('locker').get_mutex('Aggregator')
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
        self.timer = None

        self.__start_timer()
        app.listen_state(self.on_change, self.manager.entity_id)
        with self.mutex.lock('init'):
            self.__set_state()

    def __set_state(self):
        history = self.manager.get_history(self.interval)
        context = AggregatorContext(
            history, self.manager.datetime(), self.base_interval, self.app)
        func = eval(self.expr, {}, context.get_functions())
        value = func()
        self.callback(value)

    def __start_timer(self):
        assert self.timer is None
        self.timer = self.app.run_every(
            self.on_interval,
            self.app.datetime() + self.base_interval,
            self.base_interval.total_seconds())

    def on_change(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('on_change'):
            self.app.cancel_timer(self.timer)
            self.timer = None
            self.__set_state()
            self.__start_timer()

    def on_interval(self, kwargs):
        with self.mutex.lock('on_interval'):
            self.__set_state()


class AggregatedValue(hass.Hass):
    def initialize(self):
        self.target = self.args['target']
        self.attributes = self.args.get('attributes', {})
        self.aggregator_app = Aggregator(self, self.__set_state)

    def __set_state(self, value):
        self.set_state(self.target, state=value, attributes=self.attributes)
