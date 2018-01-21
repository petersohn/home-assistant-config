import appdaemon.appapi as appapi


class TestApp(appapi.AppDaemon):
    def initialize(self):
        self.register_endpoint(self.api_callback, 'TestApp')

    def api_callback(self, data):
        return {}, 200
