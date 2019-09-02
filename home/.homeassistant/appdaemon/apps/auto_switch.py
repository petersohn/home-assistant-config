import appdaemon.plugins.hass.hassapi as hass

import threading


class AutoSwitch(hass.Hass):
    def initialize(self):
        self.__target = self.args['target']
        self.__switch = self.args.get('switch')
        self.__reentrant = self.args.get('reentrant', False)
        self.__intended_state = None
        self.__timer = None

        self.lock = threading.Lock()

        with self.lock:
            self.listen_state(self.on_target_change, entity=self.__target)
            if self.__switch:
                self.run_in(self.initialize_state, 0)
                self.listen_state(self.on_switch_change, entity=self.__switch)
            self.__state = None
            self.run_in(lambda _: self.init(), 0)

    def init(self):
        with self.lock:
            try:
                self.__update(0)
            except:
                self.run_in(lambda _: self.init(), 1)
                raise

    def initialize_state(self, kwargs):
        with self.lock:
            switch_state = self.get_state(self.__switch)
            self.log('Switch state={}'.format(switch_state))
            if switch_state == 'on':
                self.log('Initially turning on')
                self.turn_on(self.__target)
            elif switch_state == 'off':
                self.log('Initially turning off')
                self.turn_off(self.__target)

    def auto_turn_on(self):
        with self.lock:
            self.log('turn on')
            if self.__reentrant:
                self.__update(self.__state + 1)
            else:
                self.__update(1)

    def auto_turn_off(self):
        with self.lock:
            self.log('turn off')
            if self.__reentrant:
                assert self.__state != 0
                self.__update(self.__state - 1)
            else:
                self.__update(0)

    def __update(self, state):
        self.__stop_timer()
        self.log('Got new state: {}'.format(state))
        self.__state = state

        if self.__switch and self.get_state(self.__switch) != 'auto':
            self.log('On manual mode')
            return

        if state == 0:
            self.__set_intended_state('off')
            self.turn_off(self.__target)
        else:
            self.__set_intended_state('on')
            self.turn_on(self.__target)

    def update(self):
        with self.lock:
            self.__update(self.__state)

    def __set_intended_state(self, state):
        self.log('Turning ' + state)
        if self.get_state(self.__target) != state:
            self.__intended_state = state
            self.__timer = self.run_in(self.update, 10)

    def on_switch_change(self, entity, attribute, old, new, kwargs):
        with self.lock:
            if new == 'on':
                self.log('Manually turning on')
                self.turn_on(self.__target)
                self.__stop_timer()
            elif new == 'off':
                self.log('Manually turning off')
                self.turn_off(self.__target)
                self.__stop_timer()
            else:
                self.log('Setting to auto')
                self.__update(self.__state)

    def on_target_change(self, entity, attribute, old, new, kwargs):
        with self.lock:
            if not self.__intended_state and self.__switch:
                self.log('Switching to manual mode')
                self.select_option(entity_id=self.__switch, option=new)
                self.__intended_state = None
                self.__stop_timer()
            elif new == self.__intended_state:
                self.__intended_state = None
                self.__stop_timer()

    def __stop_timer(self):
        if self.__timer:
            self.cancel_timer(self.__timer)
            self.__timer = None


class Switcher:
    def __init__(self, auto_switch):
        self.lock = threading.Lock()
        self.auto_switch = auto_switch
        self.state = False

    def turn_on(self):
        with self.lock:
            if not self.state:
                self.auto_switch.auto_turn_on()
                self.state = True

    def turn_off(self):
        with self.lock:
            if self.state:
                self.auto_switch.auto_turn_off()
                self.state = False


class MultiSwitcher:
    def __init__(self, app, targets):
        self.app = app
        self.targets = [Switcher(app.get_app(target)) for target in targets]

    def turn_on(self):
        for target in self.targets:
            target.turn_on()

    def turn_off(self):
        for target in self.targets:
            target.turn_off()
