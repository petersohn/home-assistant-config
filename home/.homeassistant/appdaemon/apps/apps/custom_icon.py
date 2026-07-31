from __future__ import annotations
import hass
from hass_common import EntityValue
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import locker


class CustomIcon(hass.Hass):
    off_icon: str = ""
    on_icon: str = ""
    mutex: locker.Mutex | None = None

    def initialize(self) -> None:
        self.off_icon = self.args["off_icon"]
        self.on_icon = self.args["on_icon"]

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
        old: EntityValue,
        new: EntityValue,
        **kwargs: Any,
    ) -> None:
        pass
        # self.log('lofasz')
        # with self.mutex.lock('on_changed'):
        #     state = self.get_state(entity=entity, attribute='all')
        #     icon = self.on_icon if state['state'] == 'on' else self.off_icon
        #     state['attributes']['icon'] = icon
        #     self.log(f"set state: {state['attributes']}")
        #     self.set_state(entity, attributes=state['attributes'])
