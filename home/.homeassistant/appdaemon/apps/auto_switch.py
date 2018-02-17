import appdaemon.appapi as appapi

class AutoSwitch:

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

class Dummy(appapi.AppDaemon):
    pass
