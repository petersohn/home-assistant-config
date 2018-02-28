import appdaemon.appapi as appapi


class TestOtherApp(appapi.AppDaemon):
    def initialze(self):
        pass

    def other_test(self, arg):
        return arg
