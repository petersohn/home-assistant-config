import appdaemon.plugins.hass.hassapi as hass


class CustomIcon(hass.Hass):
    def initialize(self):
        self.off_icon = self.args['off_icon']
        self.on_icon = self.args['on_icon']

        self.mutex = self.get_app('locker').get_mutex('CustomIcon')

        for entity in self.args['entities']:
            self.listen_state(self.on_changed, entity=entity)

    def on_changed(self, entity, attribute, old, new, kwargs):
        if old == new:
            return
        with self.mutex.lock('on_changed'):
            state = self.get_state(entity=entity, attribute='all')
            icon = self.on_icon if state['state'] == 'on' else self.off_icon
            state['attributes']['icon'] = icon
            self.set_state(entity, attributes=state['attributes'])
