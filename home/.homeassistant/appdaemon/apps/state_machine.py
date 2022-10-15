import appdaemon.plugins.hass.hassapi as hass

from expression import ExpressionEvaluator

import copy
from pprint import pformat


class Action:
    def __init__(self, app, name, data):
        self.app = app
        self.name = name

        services = data['service']
        if type(services) is list:
            self.calls = [
                (service['service'], service['args']) for service in services]
        else:
            self.calls = [(services['service'], services['args'])]

    def execute(self):
        self.app.log('Execute action: {}'.format(self.name))
        for service, args in self.calls:
            self.app.call_service(service, **args)


class State:
    def __init__(self, app, name, data, actions):
        self.app = app
        self.name = name
        self.switch = data.get('switch')
        enter_action = data.get('enter_action')
        self.enter_action = actions[enter_action] \
            if enter_action is not None else None
        exit_action = data.get('exit_action')
        self.exit_action = actions[exit_action] \
            if exit_action is not None else None
        self.is_active = False

        if self.switch:
            self.listen_handle = self.app.listen_state(
                self.on_switch_change, entity=self.switch)
        else:
            self.listen_handle = None

        locker = self.app.get_app('locker')
        self.state_mutex = locker.get_mutex('State.State')
        self.callback_mutex = locker.get_mutex('State.Callback')

    def cleanup(self):
        if self.listen_handle is not None:
            self.app.cancel_listen_state(self.listen_handle)

    def on_switch_change(self, entity, attribute, old, new, kwargs):
        active = new == 'on'
        with self.callback_mutex.lock('on_switch_change'):
            with self.state_mutex.lock('on_switch_change'):
                if active == self.is_active:
                    return

            if active:
                self.app.change_state(self.name)
            else:
                self.app.reset_state()

    def enter(self):
        with self.state_mutex.lock('enter'):
            if self.is_active:
                return

            self.app.log('Enter state: {}'.format(self.name))
            if self.switch is not None:
                self.app.turn_on(self.switch)
            if self.enter_action is not None:
                self.enter_action.execute()
            self.is_active = True

    def exit(self):
        with self.state_mutex.lock('enter'):
            if not self.is_active:
                return

            self.app.log('Exit state: {}'.format(self.name))
            if self.exit_action is not None:
                self.exit_action.execute()
            self.turn_off()
            self.is_active = False

    def turn_off(self):
        if self.switch is not None:
            self.app.turn_off(self.switch)


class Trigger:
    def __init__(self, app, name, data):
        self.app = app
        self.name = name
        self.next_state = data['next_state']

        states = data.get('state')
        if type(states) is str:
            self.states = [states]
        else:
            assert(states is None or type(states) is list)
            self.states = states

        self.is_active = False

        locker = self.app.get_app('locker')
        self.state_mutex = locker.get_mutex('Trigger.State')
        self.callback_mutex = locker.get_mutex('Trigger.Callback')

    def call_back(self):
        with self.callback_mutex.lock('call_back'):
            with self.state_mutex.lock('call_back'):
                if not self.is_active:
                    return
            self.app.log('Execute trigger: {}'.format(self.name))
            self.app.change_state(self.next_state)

    def cleanup(self):
        pass

    def _activate(self):
        pass

    def _deactivate(self):
        pass

    def activate(self, state):
        if state == self.next_state:
            return
        if self.states is not None and state not in self.states:
            return

        with self.state_mutex.lock('activate'):
            self.app.log('Activate trigger: {}'.format(self.name))
            if not self.is_active:
                self.is_active = True
                self._activate()

    def deactivate(self):
        with self.state_mutex.lock('deactivate'):
            self.app.log('Deactivate trigger: {}'.format(self.name))
            if self.is_active:
                self.is_active = False
                self._deactivate()


class TimeTrigger(Trigger):
    def __init__(self, app, name, data):
        super(TimeTrigger, self).__init__(app, name, data)
        self.interval = datetime.timedelta(**data['interval'])
        self.timer = None

    def cleanup(self):
        if self.timer is not None:
            self.app.cancel_timer(self.timer)

    def _activate(self):
        self.timer = self.app.run_in(
            lambda _: self.call_back(),
            self.interval.total_seconds())

    def _deactivate(self):
        self.app.cancel_timer(self.timer)
        self.timer = None


class ExpressionTrigger(Trigger):
    def __init__(self, app, name, data):
        super(ExpressionTrigger, self).__init__(app, name, data)
        self.condition = ExpressionEvaluator(
            self.app, data['expr'], self._on_change)

    def cleanup(self):
        self.condition.cleanup()

    def _on_change(self, value):
        if value:
            self.call_back()

    def _activate(self):
        self.app.run_in(lambda _: self.__activate(), 0)

    def __activate(self):
        value = self.condition.get()
        if value:
            self.call_back()


class StateMachine(hass.Hass):
    def initialize(self):
        entities = self.args.get('entities')
        actions = self.args['actions']
        for action in actions.values():
            action.setdefault('entities', entities)
        self.actions = {
            name: Action(self, name, action) for name, action in actions.items()
        }
        self.states = {
            name: State(self, name, state, self.actions)
            for name, state in self.args['states'].items()
        }

        def create_trigger(name, data):
            trigger_type = data['type']
            if trigger_type == 'time':
                return TimeTrigger(self, name, data)
            elif trigger_type == 'condition':
                return ExpressionTrigger(self, name, data)
            else:
                raise RuntimeError(
                    'Invalid trigger type: {}'.format(trigger_type))

        self.triggers = {
            name: create_trigger(name, trigger)
            for name, trigger in self.args['triggers'].items()
        }
        self.default_state = self.args['default_state']
        self.current_state = None

        self.mutex = self.get_app('locker').get_mutex('StateMachine')
        self.run_in(lambda _: self.init_state(), 0)

    def terminate(self):
        for trigger in self.triggers.values():
            trigger.cleanup()
        for state in self.states.values():
            state.cleanup()

    def init_state(self):
        with self.mutex.lock('init_state'):
            if self.current_state != None:
                self.log('Already initialized')
                return

            beginning_state = self.default_state
            for name, state in self.states.items():
                if state.switch is not None and self.get_state(state.switch) == 'on':
                    beginning_state = name
                    break
            for state in self.states.values():
                if state != beginning_state:
                    state.turn_off()
            self._change_state(beginning_state)

    def reset_state(self):
        with self.mutex.lock('reset_state'):
            self._change_state(self.default_state)

    def change_state(self, state):
        with self.mutex.lock('change_state'):
            self._change_state(state)

    def _change_state(self, state):
        if state not in self.states:
            raise RuntimeError('Invalid state: {}'.format(state))

        self.log('State change: {} -> {}'.format(self.current_state, state))

        if self.current_state is not None:
            self._deactivate_triggers()
            self.states[self.current_state].exit()
        self.current_state = state
        self.states[state].enter()
        self._activate_triggers()

    def _activate_triggers(self):
        for trigger in self.triggers.values():
            trigger.activate(self.current_state)

    def _deactivate_triggers(self):
        for trigger in self.triggers.values():
            trigger.deactivate()
