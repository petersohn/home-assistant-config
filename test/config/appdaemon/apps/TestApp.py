import appdaemon.appapi as appapi

import Blocker

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
            self.log(
                'Calling function: ' + function + ' ' + str(args) +
                ' ' + str(kwargs))
            result = getattr(self, function)(*args, **kwargs)
            self.log('Function returns: ' + function + ' = ' + str(result))
            return result, 200
        except:
            return traceback.format_exc(), 500

    def test(self, arg):
        self.log(str(type(self.time())))
        return arg

    def __block(self, kwargs):
        Blocker.block()

    def unblock_until(self, timestamp):
        self.run_at(self.__block, datetime.datetime.fromtimestamp(timestamp))
        Blocker.unblock()

    def unblock_for(self, duration):
        self.run_in(self.__block, duration)
        Blocker.unblock()

    def get_current_time(self):
        return self.datetime().timestamp()
