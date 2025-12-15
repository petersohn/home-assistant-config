import hass


class HistoryWatcher(hass.Hass):
    def do_initialize(self):
        self.state_history = []
        self.entities = self.args.get("entities")
        self.mutex = self.get_app("locker").get_mutex("TestApp")
        with self.mutex.lock("init"):
            for entity in self.entities:
                self.listen_state(self.on_change, entity)

    def on_change(self, entity, attribute, old, new, kwargs):
        with self.mutex.lock("on_change"):
            self.log("{} = {}".format(entity, new))
            self.state_history.append((entity, new))

    def get_history(self):
        with self.mutex.lock("get_history"):
            result = self.state_history
            self.state_history = []
            return result

    def has_history(self, history):
        assert len(history) != 0
        with self.mutex.lock("get_history"):
            i = 0
            for item in self.state_history:
                if item == tuple(history[i]):
                    i += 1
                    if i == len(history):
                        return True
            return False
