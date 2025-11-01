from collections import namedtuple


#StateCallback = namedtuple('StateCallback', callback, entity, attribute, 

class AppManager:
    def __init__(self):
        self.__apps = {}
        self.__states = {}
        self.__state_callbacks = {}
        self.__state_callback_id = 0

    def add_app(self, name, app, args):
        app.init_app(self, args)
        self.__apps[name] = app

    def get_app(self, name):
        return self.__apps[name]

    def get_state(self, name):
        return self.__states.get(name)

    def set_state(self, name, state, attributes = {}):
        self.__states[name] = value


class Hass:
    def __init__(self):
        self.__manager = None
        self.args = {}

    def init_app(self, manager, args):
        self.__manager = manager
        self.args = args

    def get_app(self, name):
        return self.__manager.get_app(name)

    def get_state(self, name):
        return self.__manager.get_state(name)

    def set_state(self, name, value):
        self.__manager.set_state(name, value)
