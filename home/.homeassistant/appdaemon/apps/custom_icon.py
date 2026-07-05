from __future__ import annotations
import hass
from typing import Any


class CustomIcon(hass.Hass):
    def initialize(self) -> None:
        self.off_icon: str = self.args["off_icon"]
        self.on_icon: str = self.args["on_icon"]

        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("CustomIcon")

        self.log("asdasd")
        for entity in self.args["entities"]:
            self.listen_state(self.on_changed, entity_id=entity)

    def on_changed(
        self,
        entity: str,
        attribute: str | None,
        old: Any,
        new: Any,
        **kwargs: Any,
    ) -> None:
        pass
        # self.log('lofasz')
        # with self.mutex.lock('on_changed'):
        #     state = self.get_state(entity=entity, attribute='all')
        #     icon = self.on_icon if state['state'] == 'on' else self.off_icon
        #     state['attributes']['icon'] = icon
        #     self.log("set state: {}".format(state['attributes']))
        #     self.set_state(entity, attributes=state['attributes'])
