import hass


class CustomIcon(hass.Hass):
    def do_initialize(self):
        self.off_icon = self.args["off_icon"]
        self.on_icon = self.args["on_icon"]

        self.mutex = self.get_app("locker").get_mutex("CustomIcon")

        for entity in self.args["entities"]:
            self.listen_state(self.on_changed, entity)

    def on_changed(self, entity, attribute, old, new, kwargs):
        pass
        # self.log('lofasz')
        # with self.mutex.lock('on_changed'):
        #    state = self.get_state(entity=entity, attribute='all')
        #    icon = self.on_icon if state['state'] == 'on' else self.off_icon
        #    state['attributes']['icon'] = icon
        #    self.log("set state: {}".format(state['attributes']))
        #    self.set_state(entity, attributes=state['attributes'])
