import appdaemon.plugins.hass.hassapi as hass


class AutoSwitch(hass.Hass):
    def initialize(self):
        self.target = self.args['target']
        self.switch = self.args.get('switch')
        self.reentrant = self.args.get('reentrant', False)
        self.intended_state = None
        self.timer = None

        self.mutex = self.get_app('locker').get_mutex('AutoSwitch')

        with self.mutex.lock('initialize'):
            self.listen_state(self.on_target_change, entity=self.target)
            if self.switch:
                self.run_in(self.initialize_state, 0)
                self.listen_state(self.on_switch_change, entity=self.switch)
            self.state = None
            self.run_in(lambda _: self.init(), 0)

    def init(self):
        with self.mutex.lock('init'):
            try:
                if self.state is None:
                    self.__update(0)
            except:
                self.run_in(lambda _: self.init(), 1)
                raise

    def initialize_state(self, kwargs):
        with self.mutex.lock('initialize_state'):
            switch_state = self.get_state(self.switch)
            self.log('Switch state={}'.format(switch_state))
            if switch_state == 'on':
                self.log('Initially turning on')
                self.turn_on(self.target)
            elif switch_state == 'off':
                self.log('Initially turning off')
                self.turn_off(self.target)

    def auto_turn_on(self):
        with self.mutex.lock('auto_turn_on'):
            self.log('turn on')
            if self.reentrant:
                if self.state is None:
                    self.state = 0
                self.__update(self.state + 1)
            else:
                self.__update(1)

    def auto_turn_off(self):
        with self.mutex.lock('auto_turn_off'):
            self.log('turn off')
            if self.reentrant:
                assert self.state != 0
                self.__update(self.state - 1)
            else:
                self.__update(0)

    def __update(self, state):
        self.__stop_timer()
        self.log('Got new state: {} -> {}'.format(self.state, state))
        self.state = state

        if self.switch and self.get_state(self.switch) != 'auto':
            self.log('On manual mode')
            return

        if state == 0:
            self.__set_intended_state('off')
            self.turn_off(self.target)
        else:
            self.__set_intended_state('on')
            self.turn_on(self.target)

    def update(self, kwargs):
        with self.mutex.lock('update'):
            self.__update(self.state)

    def __set_intended_state(self, state):
        self.log('Turning ' + state)
        if self.get_state(self.target) != state:
            self.intended_state = state
            self.timer = self.run_in(self.update, 10)

    def on_switch_change(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('on_switch_change'):
            value = self.get_state(entity)
            if value == 'on':
                self.log('Manually turning on')
                self.turn_on(self.target)
                self.__stop_timer()
            elif value == 'off':
                self.log('Manually turning off')
                self.turn_off(self.target)
                self.__stop_timer()
            else:
                self.log('Setting to auto')
                self.__update(self.state)

    def on_target_change(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock('on_target_change'):
            value = self.get_state(entity)
            if not self.intended_state:
                if self.switch is None or self.get_state(self.switch) == 'auto':
                    self.log('State change detected: {}'.format(value))
                    self.__update(self.state)
                else:
                    self.select_option(entity_id=self.switch, option=value)
            elif value == self.intended_state:
                self.intended_state = None
                self.__stop_timer()

    def __stop_timer(self):
        if self.timer:
            self.cancel_timer(self.timer)
            self.timer = None


class Switcher:
    def __init__(self, auto_switch):
        self.mutex = auto_switch.get_app('locker').get_mutex('Switcher')
        self.auto_switch = auto_switch
        self.state = False

    def turn_on(self):
        with self.mutex.lock('turn_on'):
            if not self.state:
                self.auto_switch.auto_turn_on()
                self.state = True

    def turn_off(self):
        with self.mutex.lock('turn_off'):
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
