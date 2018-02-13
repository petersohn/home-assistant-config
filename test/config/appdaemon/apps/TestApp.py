import appdaemon.appapi as appapi

import TestAppDaemon

import datetime
import traceback


class TestApp(appapi.AppDaemon):
    def initialize(self):
        self.register_endpoint(self.api_callback, 'TestApp')

    def api_callback(self, data):
        args = data.get('args', [])
        kwargs = data.get('kwargs', {})
        try:
            function = data['function']
            self.log('Calling function: ' + function)
            result = getattr(self, function)(*args, **kwargs)
            return result, 200
        except:
            return traceback.format_exc(), 500

    def test(self, arg):
        self.log(str(type(self.time())))
        return arg

    def unblock_until(self, timestamp):
        self.run_at(TestAppDaemon.block, datetime.fromtimestamp(timestamp))
        TestAppDaemon.unblock()

    def unblock_for(self, duration):
        self.run_in(TestAppDaemon.block, duration)
        TestAppDaemon.unblock()

    def get_current_time(self):
        return self.datetime().timestamp()
