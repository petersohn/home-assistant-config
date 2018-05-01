import appdaemon.plugins.hass.hassapi as hass


class AutoSwitch(hass.Hass):
    def initialize(self):
        self.__target = self.args['target']
        self.__switch = self.args.get('switch')
        self.__reentrant = self.args.get('reentrant', False)
        self.__intended_state = None

        self.listen_state(self.__on_target_change, entity=self.__target)

        if self.__switch:
            self.run_in(self.__initialize_state, 0)
            self.listen_state(self.__on_switch_change, entity=self.__switch)
        self.__state = None
        self.run_in(lambda _: self.__update(0), 0)

    def __initialize_state(self, kwargs):
        switch_state = self.get_state(self.__switch)
        self.log('Switch state=' + switch_state)
        if switch_state == 'on':
            self.log('Initially turning on')
            self.turn_on(self.__target)
        elif switch_state == 'off':
            self.log('Initially turning off')
            self.turn_off(self.__target)

    def auto_turn_on(self):
        if self.__reentrant:
            self.__update(self.__state + 1)
        else:
            self.__update(1)

    def auto_turn_off(self):
        if self.__reentrant:
            assert self.__state != 0
            self.__update(self.__state - 1)
        else:
            self.__update(0)

    def __update(self, state):
        self.log('Got new state: ' + str(state))
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

    def __set_intended_state(self, state):
        self.log('Turning ' + state)
        if self.get_state(self.__target) != state:
            self.__intended_state = state

    def __on_switch_change(self, entity, attribute, old, new, kwargs):
        if new == 'on':
            self.log('Manually turning on')
            self.turn_on(self.__target)
        elif new == 'off':
            self.log('Manually turning off')
            self.turn_off(self.__target)
        else:
            self.log('Setting to auto')
            self.__update(self.__state)

    def __on_target_change(self, entity, attribute, old, new, kwargs):
        if not self.__intended_state and self.__switch:
            self.log('Switching to manual mode')
            self.call_service(
                'input_select/select_option', entity_id=self.__switch,
                option=new)
            self.__intended_state = None
        elif new == self.__intended_state:
            self.__intended_state = None


class Switcher:
    def __init__(self, auto_switch):
        self.__auto_switch = auto_switch
        self.__state = False

    def turn_on(self):
        if not self.__state:
            self.__auto_switch.auto_turn_on()
            self.__state = True

    def turn_off(self):
        if self.__state:
            self.__auto_switch.auto_turn_off()
            self.__state = False
