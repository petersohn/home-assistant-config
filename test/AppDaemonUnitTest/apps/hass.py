from collections import namedtuple
from copy import deepcopy

class State:
    def __init__(self):
        self.state = None
        self.attributes = {}

    def to_map(self):
        return {'state': self.state, 'attributes': copy.deepcopy(self.attributes)}

StateCallback = namedtuple('StateCallback', ['callback', 'entity', 'attribute', 'old', 'new'])

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

    def get_state(self, name, attribute=None):
        data = self.__states.get(name)
        if data is None:
            return None
        if attribute is None:
            return data.state
        if attribute == 'all':
            return deepcopy(data.attributes)
        return state.attributes.get(attribute)

    def set_state(self, name, state, attributes={}):
        data = self.__states.setdefault(name, State())
        old = data.to_map()
        data.state = None if state is None else str(state)
        data.attributes.update(attributes)

        for callback in self.__state_callbacks.values():
            if callback.entity != name:
                continue
            if callback.attribute is None:
                old_state = old['state']
                if callback.old is not None and old_state != callback.old:
                    continue
                if callback.new is not None and data.state != callback.new:
                    continue
                callback(name, None, old_state, data.state, {})
            elif callback.attribute == 'all':
                callback(name, callback.attribute, old, data.to_map(), {})
            else:
                old_attr = old['attributes'].get(callback.attribute)
                new_attr = data.attributes.get(callback.attribute)
                if callback.old is not None and old_attr != callback.old:
                    continue
                if callback.new is not None and new_attr != callback.new:
                    continue
                callback(name, callback.attribute, old_attr, new_attr, {})


    def listen_state(self, callback, entity, attribute=None, old=None, new=None):
        id = self.__state_callback_id
        self.__state_callback_id += 1
        self.__state_callbacks[id] = StateCallback(callback, entity, attribute, new, old)

    def cancel_listen_state(self, id):
        del self.__state_callbacks[id]


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

    def set_state(self, name, state, attributes):
        self.__manager.set_state(name, state, attributes)
        
    def listen_state(self, callback, entity, attribute=None, old=None, new=None):
        self.__manager.listen_state(callback, entity, attribute, old, new)

    def cancel_listen_state(self, id):
        self.__manager.cancel_listen_state(id)
