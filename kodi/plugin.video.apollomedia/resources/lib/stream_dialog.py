import xbmcgui


ACTION_BACKSPACE = 110
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_CONTEXT_MENU = 117


class StreamChooserDialog(xbmcgui.WindowXMLDialog):
    LIST_ID = 100

    def __init__(self, *args, streams=None, flags=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.streams = streams or []
        self.flags = flags or {}
        self.result = None

    def onInit(self):
        control = self.getControl(self.LIST_ID)
        items = []

        for row in self.streams:
            stream = row["stream"]
            original_index = int(row["index"])
            url = str(stream.get("url") or "")
            flag = self.flags.get(url)

            title = (
                stream.get("title")
                or stream.get("description")
                or "Unknown stream"
            )

            item = xbmcgui.ListItem(label=title)
            item.setProperty("Apollo.Index", str(original_index))
            item.setProperty("Apollo.Provider", str(stream.get("provider") or ""))
            item.setProperty("Apollo.Description", str(stream.get("description") or ""))
            item.setProperty("Apollo.Flagged", "true" if flag else "false")
            item.setProperty(
                "Apollo.FlagReason",
                str((flag or {}).get("reason") or "").replace("_", " ").title(),
            )
            items.append(item)

        control.addItems(items)
        try:
            control.selectItem(0)
        except Exception:
            pass

    def _selected_item(self):
        try:
            return self.getControl(self.LIST_ID).getSelectedItem()
        except Exception:
            return None

    def _selected_index(self):
        item = self._selected_item()
        if not item:
            return None
        try:
            return int(item.getProperty("Apollo.Index"))
        except Exception:
            return None

    def _selected_flagged(self):
        item = self._selected_item()
        return bool(item and item.getProperty("Apollo.Flagged") == "true")

    def _play_selected(self):
        index = self._selected_index()
        if index is not None:
            self.result = ("play", index)
            self.close()

    def _context_selected(self):
        index = self._selected_index()
        if index is None:
            return

        flagged = self._selected_flagged()
        options = ["Play", "Unflag Stream" if flagged else "Flag Stream"]
        choice = xbmcgui.Dialog().contextmenu(options)

        if choice == 0:
            self.result = ("play", index)
            self.close()
        elif choice == 1:
            self.result = ("unflag" if flagged else "flag", index)
            self.close()

    def onClick(self, control_id):
        if control_id == self.LIST_ID:
            self._play_selected()

    def onAction(self, action):
        action_id = action.getId()

        if action_id == ACTION_CONTEXT_MENU:
            self._context_selected()
            return

        if action_id in (ACTION_BACKSPACE, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
