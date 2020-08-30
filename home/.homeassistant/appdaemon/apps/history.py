import appdaemon.plugins.hass.hassapi as hass
import datetime
from dateutil import tz
from urllib import request
import http.client
import json
from collections import namedtuple, deque
import re
import traceback


HistoryElement = namedtuple('HistoryElement', ['time', 'value'])


def make_history_element(time, value):
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

    def __filter(self):
        min_time = self.datetime() - self.max_interval
        while len(self.history) >= 2 and self.history[1].time < min_time:
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
                        (make_history_element(
                            get_date(change['last_changed']),
                            change['state'])
                         for changes in loaded_history for change in changes)))
            except:
                self.error('Failed to load history.', level='WARNING')
                self.error(traceback.format_exc(), level='WARNING')
                self.run_in(self.load_config, 2)
                raise

            self.log('Total loaded history size: {}'.format(len(self.history)))
            self.__filter()
            self.log('Filtered history size: {}'.format(len(self.history)))
            self.listen_state(
                self.on_changed, entity=self.entity_id)
            self.loaded = True
            self.log('History loaded.')

    def on_changed(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('on_changed'):
            if new == old:
                return
            self.__filter()
            self.history.append(make_history_element(
                self.datetime(), self.get_state(self.entity_id)))


class Aggregatum:
    def __init__(self, app):
        self.app = app

    def add(self, element):
        raise NotImplemented

    def get(self):
        raise NotImplemented

class LimitedHistoryAggregatum(Aggregatum):
    def __init__(self, app, interval):
        super(LimitedHistoryAggregatum, self).__init__(app)
        self.interval = interval
        self.history = deque()

    def add(self, element):
        if not self.adding(element):
            self.history.append(element)
        minimum_time = element.time - self.interval
        while len(self.history) >= 2 and self.history[1].time <= minimum_time:
            removed_element = self.history.popleft()
            self.removed(removed_element)
        if self.history[0].time < minimum_time:
            old_element = self.history[0]
            self.history[0] = HistoryElement(
                minimum_time, self.history[0].value)
            self.trimmed(old_element)

    def adding(self, element):
        return False

    def removed(self, element):
        pass

    def trimmed(self, element):
        pass


class Minmax(LimitedHistoryAggregatum):
    def __init__(self, app, interval, function):
        super(Minmax, self).__init__(app, interval)
        self.value = None
        self.function = function

    def adding(self, element):
        self.app.log('Add: {}'.format(element.value))
        if self.value is None:
            if self.history:
                self._reevaluate()
            else:
                self.value = element.value
        self.value = self.function(self.value, element.value)

    def removed(self, element):
        self.app.log('remove: {}'.format(element.value))
        if abs(element.value - self.value) < 0.0001:
            self._reevaluate()

    def _reevaluate(self):
        self.value = self.function(e.value for e in self.history)

    def get(self):
        if self.value is None:
            raise ValueError
        return self.value

class Sum(LimitedHistoryAggregatum):
    def __init__(self, app, interval):
        super(Sum, self).__init__(app, interval)
        self.value = 0.0
        self.last = None

    def adding(self, element):
        if element.value == self.last:
            return True
        self.value += element.value
        self.last = element.value

    def removed(self, element):
        self.value -= element.value

    def get(self):
        return self.value


class IntervalAggragatum(LimitedHistoryAggregatum):
    def __init__(self, app, interval):
        super(IntervalAggragatum, self).__init__(app, interval)

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


class Integral(IntervalAggragatum):
    def __init__(self, app, interval, base_interval):
        super(Integral, self).__init__(app, interval)
        self.base_interval = base_interval
        self.sum = 0.0

    def get(self):
        return self.sum

    def add_interval(self, interval, value):
        seconds = interval / self.base_interval
        self.sum += value * seconds

    def remove_interval(self, interval, value):
        seconds = interval / self.base_interval
        self.sum -= value * seconds


class Mean(IntervalAggragatum):
    def __init__(self, app, interval):
        super(Mean, self).__init__(app, interval)
        self.sum = 0.0
        self.time = 0.0

    def get(self):
        self.app.log('sum={}, time={}'.format(self.sum, self.time))
        if self.time == 0.0:
            raise ValueError
        return self.sum / self.time

    def add_interval(self, interval, value):
        seconds = interval.total_seconds()
        self.app.log('Add: t={}, v={}'.format(seconds, value))
        self.sum += value * seconds
        self.time += seconds

    def remove_interval(self, interval, value):
        seconds = interval.total_seconds()
        self.app.log('Remove: t={}, v={}'.format(seconds, value))
        self.sum -= value * seconds
        self.time -= seconds


class Anglemean(IntervalAggragatum):
    def __init__(self, app, interval):
        super(Anglemean, self).__init__(app, interval)
        self.sum180 = 0.0
        self.sum360 = 0.0
        self.sum360_2 = 0.0
        self.sum180_2 = 0.0
        self.time = 0.0

    def get(self):
        if self.time == 0.0:
            raise ValueError
        varsum180 = self.sum180_2 - (self.sum180 ** 2) / self.time
        varsum360 = self.sum360_2 - (self.sum360 ** 2) / self.time
        self.app.log('sum180={}, sum180_2={}, varsum180={}'.format(
            self.sum180, self.sum180_2, varsum180))
        self.app.log('sum360={}, sum360_2={}, varsum360={}'.format(
            self.sum360, self.sum360_2, varsum360))
        self.app.log('time={}'.format(self.time))
        if varsum180 < varsum360:
            result = self.sum180 / self.time
            if result < 0:
                result += 360
            return result
        else:
            return self.sum360 / self.time

    def add_interval(self, interval, value):
        value360 = value % 360  # this should be < 360 anyway
        value180 = value - 360 if value > 180 else value
        seconds = interval.total_seconds()
        self.app.log('Add: t={}, v180={}, v360={}'.format(
            seconds, value180, value360))
        self.sum180 += value180 * seconds
        self.sum180_2 += (value180 ** 2) * seconds
        self.sum360 += value360 * seconds
        self.sum360_2 += (value360 ** 2) * seconds
        self.time += seconds

    def remove_interval(self, interval, value):
        value360 = value % 360  # this should be < 360 anyway
        value180 = value - 360 if value > 180 else value
        seconds = interval.total_seconds()
        self.app.log('Remove: t={}, v180={}, v360={}'.format(
            seconds, value180, value360))
        self.sum180 -= value180 * seconds
        self.sum180_2 -= (value180 ** 2) * seconds
        self.sum360 -= value360 * seconds
        self.sum360_2 -= (value360 ** 2) * seconds
        self.time -= seconds


class DecaySum(Aggregatum):
    def __init__(self, app, interval, fraction):
        super(DecaySum, self).__init__(app)
        self.interval = interval.total_seconds()
        self.fraction = fraction
        self.value = None
        self.last = None
        self.time = None

    def add(self, element):
        if self.time is None:
            self.time = element.time
            self.value = element.value
            return

        diff = (element.time - self.time).total_seconds()
        self.value *= self.fraction ** (diff / self.interval)
        if self.last != element.value:
            self.value += element.value
            self.last = element.value
        self.time = element.time

    def get(self):
        return self.value


class Aggregator:
    def __init__(self, app, callback):
        self.mutex = app.get_app('locker').get_mutex('Aggregator')
        self.app = app
        self.base_interval = datetime.timedelta(
            **app.args.get('base_interval', {'minutes': 1}))
        self.aggregatum = self.get_aggregatum(app.args['aggregator'])
        self.callback = callback
        self.timer = None

        self.manager = app.get_app(app.args['manager'])
        history = self.manager.get_history()
        for element in history:
            self.aggregatum.add(element)
        if not history:
            element = make_history_element(
                self.app.datetime(), self.app.get_state(self.manager.entity_id))
            self.aggregatum.add(element)

        app.listen_state(self.on_change, self.manager.entity_id)
        with self.mutex.lock('init'):
            self.__start_timer()
            self.__set_state()

    def get_aggregatum(self, name):
        def get_interval():
            return datetime.timedelta(**self.app.args['interval'])
        aggregators = {
            "min": lambda: Minmax(self.app, get_interval(), min),
            "max": lambda: Minmax(self.app, get_interval(), max),
            "sum": lambda: Sum(self.app, get_interval()),
            "integral": lambda: Integral(
                self.app, get_interval(), self.base_interval),
            "mean": lambda: Mean(self.app, get_interval()),
            "anglemean": lambda: Anglemean(self.app, get_interval()),
            "decay_sum": lambda: DecaySum(
                self.app, get_interval(), self.app.args['fraction']),
        }
        return aggregators[name]()

    def __set_state(self):
        try:
            value = self.aggregatum.get()
        except ValueError:
            return
        self.callback(value)

    def __start_timer(self):
        assert self.timer is None
        self.timer = self.app.run_every(
            self.on_interval,
            self.app.datetime() + self.base_interval,
            self.base_interval.total_seconds())

    def on_change(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('on_change'):
            element = make_history_element(self.app.datetime(), new)
            self.aggregatum.add(element)
            self.app.cancel_timer(self.timer)
            self.timer = None
            self.__set_state()
            self.__start_timer()

    def on_interval(self, kwargs):
        with self.mutex.lock('on_interval'):
            element = make_history_element(
                self.app.datetime(), self.app.get_state(self.manager.entity_id))
            self.aggregatum.add(element)
            self.__set_state()


class AggregatedValue(hass.Hass):
    def initialize(self):
        self.target = self.args['target']
        self.attributes = self.args.get('attributes', {})
        self.aggregator_app = Aggregator(self, self.__set_state)

    def __set_state(self, value):
        self.set_state(self.target, state=value, attributes=self.attributes)
