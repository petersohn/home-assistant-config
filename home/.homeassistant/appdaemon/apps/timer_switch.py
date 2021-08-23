import appdaemon.plugins.hass.hassapi as hass
import auto_switch
import traceback


class Trigger:
    def __init__(self, app, expr, sensor, source_state, target_state, callback):
        self.app = app
        self.callback = callback
        self.expression = None
        self.saved_state = None
        self.sensor = None
        self.source_state = None
        self.target_state = None
        self.mutex = self.app.get_app('locker').get_mutex('Trigger')
        if expr is not None:
            import expression
            self.expression = expression.ExpressionEvaluator(
                self.app, expr, self.on_expression_change)
            self.saved_state = self.expression.get() is True
        else:
            self.sensor = sensor
            self.source_state = source_state
            self.target_state = target_state
            self.saved_state = self.source_state is None and \
                self.app.get_state(self.sensor) == self.target_state
            self.app.listen_state(self.on_state_change, entity=self.sensor)

    def cleanup(self):
        if self.expression is not None:
            self.expression.cleanup()

    def is_on(self):
        return self.saved_state

    def _on_change(self, new_on):
        if new_on != self.saved_state:
            self.saved_state = new_on
            self.callback(new_on)

    def on_state_change(self, entity, attribute, old, new, kwargs):
        self.app.log('state changed: {} -> {} target={} -> {}'.format(
            old, new, self.source_state, self.target_state))
        with self.mutex.lock('on_state_change'):
            self._on_change(new == self.target_state and (
                self.source_state is None or old == self.source_state))

    def on_expression_change(self, value):
        with self.mutex.lock('on_expression_change'):
            self._on_change(value is True)


class Timer:
    def __init__(self, app, time, callback):
        self.app = app
        try:
            self.time = float(time) * 60
        except ValueError:
            self.time = time
        self.callback = callback
        self.timer = None
        self.mutex = self.app.get_app('locker').get_mutex('Timer')

    def stop(self):
        with self.mutex.lock('stop'):
            if self.timer is not None:
                self.app.cancel_timer(self.timer)
                self.timer = None

    def start(self):
        with self.mutex.lock('start'):
            if type(self.time) is float:
                time = self.time
            else:
                try:
                    time = float(self.app.get_state(self.time)) * 60
                except Exception:
                    self.app.error(traceback.format_exc())
                    time = 0
            self.timer = self.app.run_in(self.on_timeout, time)

    def is_running(self):
        with self.mutex.lock('is_running'):
            return self.timer is not None

    def on_timeout(self, kwargs):
        with self.mutex.lock('on_timeout'):
            self.timer = None
        self.callback()


class TimerSwitch(hass.Hass):
    def initialize(self):
        self.trigger = Trigger(
            app=self,
            expr=self.args.get('expr'),
            sensor=self.args.get('sensor'),
            source_state=None,
            target_state=self.args.get('target_state', 'on'),
            callback=self.on_change)
        self.targets = auto_switch.MultiSwitcher(self, self.args['targets'])
        enabler = self.args.get('enabler')
        if enabler is not None:
            self.enabler = self.get_app(enabler)
            self.enabler_id = self.enabler.add_callback(self.on_enabled_changed)
        else:
            self.enabler = None
            self.enabler_id = None

        self.mutex = self.get_app('locker').get_mutex('TimerSwitch')
        with self.mutex.lock('initialize'):
            self.timer = Timer(self, self.args['time'], self.on_timeout)
            self.was_enabled = None
            self.is_on = self.trigger.is_on()
            self.run_in(lambda _: self.on_enabled_changed(), 0)

    def terminate(self):
        self.trigger.cleanup()
        self.targets.turn_off()
        if self.enabler is not None:
            self.enabler.remove_callback(self.enabler_id)

    def on_enabled_changed(self):
        with self.mutex.lock('on_enabled_changed'):
            self._set_enabled()

    def _set_enabled(self):
        enabled = self.enabler is None or self.enabler.is_enabled()
        if self.was_enabled != enabled:
            self.was_enabled = enabled
            self.log('enabled changed to {}'.format(enabled))
            if enabled:
                if self.is_on:
                    self.__start()
            else:
                self.timer.stop()
                self.targets.turn_off()

    def __handle_start(self):
        if self.enabler is None or self.enabler.is_enabled():
            self.__start()

    def on_change(self, value):
        with self.mutex.lock('on_change'):
            self.log('on_change: {}'.format(value))
            self.is_on = value
            if value:
                self.__handle_start()
            else:
                self.__handle_stop()

    def __handle_stop(self):
        if not self.timer.is_running():
            self.timer.start()

    def __start(self):
        self.timer.stop()
        self.log('Turn on')
        self.targets.turn_on()

    def on_timeout(self):
        with self.mutex.lock('on_timeout'):
            self.log('Turn off')
            self.targets.turn_off()


class SequenceElement:
    def __init__(self, timer, targets):
        self.timer = timer
        self.targets = targets


class TimerSequence(hass.Hass):
    def initialize(self):
        self.sequence = [SequenceElement(
            Timer(self, element['time'], self.on_timeout),
            auto_switch.MultiSwitcher(self, element['targets']))
            for element in self.args['sequence']]

        self.trigger = Trigger(
            app=self,
            expr=self.args.get('expr'),
            sensor=self.args.get('sensor'),
            source_state=self.args.get('source_state'),
            target_state=self.args.get('target_state', 'on'),
            callback=self.on_change)

        enabler = self.args.get('enabler')
        if enabler is not None:
            self.enabler = self.get_app(enabler)
            self.enabler_id = self.enabler.add_callback(self.on_enabled_changed)
        else:
            self.enabler = None
            self.enabler_id = None

        self.current_index = None
        self.mutex = self.get_app('locker').get_mutex('TimerSwitch')

    def terminate(self):
        self.trigger.cleanup()
        for element in self.sequence:
            element.targets.turn_off()
        if self.enabler is not None:
            self.enabler.remove_callback(self.enabler_id)

    def on_enabled_changed(self):
        with self.mutex.lock('on_enabled_changed'):
            if not self.enabler.is_enabled() \
                    and self.current_index is not None:
                element = self.sequence[self.current_index]
                element.timer.stop()
                element.targets.turn_off()
                self.current_index = None

    def on_change(self, value):
        if not value:
            return

        with self.mutex.lock('on_change'):
            if (self.enabler is None or self.enabler.is_enabled()) \
                    and self.current_index is None:
                self.current_index = 0
                self.__start()

    def __start(self):
        if self.current_index == len(self.sequence):
            self.current_index = None
            return

        element = self.sequence[self.current_index]
        element.targets.turn_on()
        element.timer.start()

    def on_timeout(self):
        with self.mutex.lock('on_timeout'):
            if self.current_index is None:
                return
            self.sequence[self.current_index].targets.turn_off()
            self.current_index += 1
            self.__start()
