# Apollo Media Server 0.1.4

This development build adds the first real integration setup flow: Jellyfin.

## Validate
1. Rebuild/reinstall the local add-on.
2. Start it and open Apollo Media from the sidebar.
3. Enter Jellyfin URL, username, and password.
4. Press **Connect Jellyfin**.
5. Apollo should show the connected server and user.
6. Press **Test connection**.

Apollo stores the Jellyfin access token, not the password.
The connection also creates/updates the first Apollo profile mapped to that Jellyfin user.

The existing Kodi addon/card remain unchanged in 0.1.4.
