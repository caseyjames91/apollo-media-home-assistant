import xbmcgui
import xbmcplugin


def literal_label(value):
    text = str(value or "")
    stripped = text.lstrip()
    if stripped and stripped[0].isdigit():
        return "\u200b" + text
    return text


def set_metadata(item, media):
    tag = item.getVideoInfoTag()
    tag.setTitle(literal_label(media.title))
    if media.plot:
        tag.setPlot(media.plot)
    if media.year:
        try:
            tag.setYear(int(media.year))
        except Exception:
            pass
    if media.ids.imdb:
        tag.setUniqueID(media.ids.imdb, "imdb")
    if media.ids.jellyfin:
        tag.setUniqueID(media.ids.jellyfin, "jellyfin")
    if media.media_type in ("episode", "season"):
        if media.season:
            tag.setSeason(int(media.season))
    if media.media_type == "episode" and media.episode:
        tag.setEpisode(int(media.episode))
        if media.show_title:
            tag.setTvShowTitle(media.show_title)

    art = {}
    if media.art.poster:
        art["poster"] = media.art.poster
        art["thumb"] = media.art.thumb or media.art.poster
    elif media.art.thumb:
        art["thumb"] = media.art.thumb
    if media.art.fanart:
        art["fanart"] = media.art.fanart
    if art:
        item.setArt(art)

    if media.resume.resumable:
        tag.setResumePoint(media.resume.position, media.resume.duration)


def add_directory_item(handle, url, media, is_folder=None):
    folder = media.is_folder if is_folder is None else is_folder
    label = media.title
    if media.in_library:
        label += "  [COLOR gray]•[/COLOR]"
    item = xbmcgui.ListItem(label=literal_label(label))
    set_metadata(item, media)
    item.setProperty("IsPlayable", "false" if folder else "true")
    remote_auto_url = media.playback.get("remote_auto_url") if getattr(media, "playback", None) else ""
    remote_choose_url = media.playback.get("remote_choose_url") if getattr(media, "playback", None) else ""
    if remote_auto_url or remote_choose_url:
        context_items = []
        if remote_auto_url:
            context_items.append((
                "Play from Stream",
                f"RunPlugin({remote_auto_url})",
            ))
        if remote_choose_url:
            context_items.append((
                "Choose Remote Stream",
                f"RunPlugin({remote_choose_url})",
            ))
        item.addContextMenuItems(context_items)
    xbmcplugin.addDirectoryItem(handle, url, item, folder)
    return item
