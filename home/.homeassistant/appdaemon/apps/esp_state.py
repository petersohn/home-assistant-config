import appdaemon.appapi as appapi


class EspStateChecker(appapi.AppDaemon):
    def initialize(self):
        name = self.args['name']
        uptime_id = 'sensor.' + name + '_uptime'
        self.listen_state(self.on_uptime_changed, uptime_id)

    def on_uptime_changed(self, entity, attribute, old, new, kwargs):
        if int(new) < int(old):
            self.call_service(
                'logbook/log', name=self.get_state(entity, 'friendly_name'),
                message='restarted', entity_id=entity)
