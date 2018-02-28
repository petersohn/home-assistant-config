import appdaemon.appapi as appapi


class AutoSwitch_:
    def __init__(self, app, entity):
        self.__app = app
        self.__entity = entity
        self.__turning_on = False
        self.__manually_turned_on = False

        self.__app.listen_state(
            self.__on_turned_on, entity=self.__entity, new='on')
        self.__app.listen_state(
            self.__on_turned_off, entity=self.__entity, new='off')

    def turn_on(self):
        self.__app.log(self.__entity + ': Turning on')
        self.__turning_on = True
        self.__app.turn_on(self.__entity)

    def turn_off(self):
        self.__turning_on = False
        if self.__manually_turned_on:
            self.__app.log(
                self.__entity + ': On manual control, not turning off')
            return

        self.__app.log(self.__entity + ': Turning off')
        self.__app.turn_off(self.__entity)

    def __on_turned_on(self, entity, attribute, old, new, kwargs):
        if self.__turning_on:
            self.__turning_on = False
        else:
            self.__app.log(self.__entity + ': Turned on manually')
            self.__manually_turned_on = True

    def __on_turned_off(self, entity, attribute, old, new, kwargs):
        self.__app.log(self.__entity + ': Turned off')
        self.__manually_turned_on = False


class AutoSwitch(appapi.AppDaemon):
    def initialize(self):
        self.__target = self.args['target']
        self.__switch = self.args.get('switch')
        self.__reentrant = self.args.get('reentrant', False)

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
            self.log('Turning off')
            self.turn_off(self.__target)
        else:
            self.log('Turning on')
            self.turn_on(self.__target)

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
