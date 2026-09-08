package com.apollo.avairbridge;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.content.SharedPreferences;
import android.media.AudioManager;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.KeyEvent;
import android.view.accessibility.AccessibilityEvent;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class GlobalKeyAccessibilityService extends AccessibilityService {
    public static final String PREFS = "apollo_ir_bridge";
    public static final String ACTION_KEY_EVENT = "com.apollo.avairbridge.GLOBAL_KEY_EVENT";

    private static final String TAG = "ApolloGlobalKeys";
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private boolean volumeKeyHeld = false;
    private int heldKeyCode = KeyEvent.KEYCODE_UNKNOWN;
    private int lockedMediaVolume = -1;
    private SharedPreferences heldPrefs;
    private String heldRemote = "";
    private String heldDevice = "";

    private final Runnable volumeRepeat = new Runnable() {
        @Override
        public void run() {
            if (!volumeKeyHeld
                    || heldPrefs == null
                    || heldRemote.isEmpty()
                    || heldDevice.isEmpty()
                    || (heldKeyCode != KeyEvent.KEYCODE_VOLUME_UP
                    && heldKeyCode != KeyEvent.KEYCODE_VOLUME_DOWN)) {
                return;
            }

            String command = heldKeyCode == KeyEvent.KEYCODE_VOLUME_UP
                    ? "volume_up"
                    : "volume_down";

            dispatchVolumeCommand(heldPrefs, heldRemote, heldDevice, command);

            // Local IR is fast enough to behave like a normal handheld remote.
            mainHandler.postDelayed(this, 105);
        }
    };

    private final Runnable volumeGuard = new Runnable() {
        @Override
        public void run() {
            if (!volumeKeyHeld || lockedMediaVolume < 0) return;

            AudioManager audio = (AudioManager) getSystemService(AUDIO_SERVICE);
            if (audio != null
                    && audio.getStreamVolume(AudioManager.STREAM_MUSIC) != lockedMediaVolume) {
                audio.setStreamVolume(AudioManager.STREAM_MUSIC, lockedMediaVolume, 0);
            }

            mainHandler.postDelayed(this, 35);
        }
    };

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();

        AccessibilityServiceInfo info = getServiceInfo();
        if (info != null) {
            info.flags |= AccessibilityServiceInfo.FLAG_REQUEST_FILTER_KEY_EVENTS;
            setServiceInfo(info);
        }

        getSharedPreferences(PREFS, MODE_PRIVATE)
                .edit()
                .putBoolean("global_key_service_connected", true)
                .apply();

        Log.i(TAG, "Accessibility service connected; global volume routing ready");
    }

    @Override
    public boolean onKeyEvent(KeyEvent event) {
        int keyCode = event.getKeyCode();

        if (keyCode != KeyEvent.KEYCODE_VOLUME_UP
                && keyCode != KeyEvent.KEYCODE_VOLUME_DOWN) {
            return false;
        }

        String keyName = KeyEvent.keyCodeToString(keyCode);
        String actionName = event.getAction() == KeyEvent.ACTION_DOWN ? "DOWN" : "UP";
        long timestamp = System.currentTimeMillis();

        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        prefs.edit()
                .putString("global_key_last_key", keyName)
                .putString("global_key_last_action", actionName)
                .putLong("global_key_last_time", timestamp)
                .apply();

        android.content.Intent intent = new android.content.Intent(ACTION_KEY_EVENT);
        intent.setPackage(getPackageName());
        intent.putExtra("key", keyName);
        intent.putExtra("action", actionName);
        intent.putExtra("time", timestamp);
        sendBroadcast(intent);

        boolean enabled = prefs.getBoolean("global_volume_enabled", false);
        String device = prefs.getString("global_volume_device", "");
        String remote = prefs.getString("global_volume_remote", "");

        if (!enabled || device.isEmpty() || remote.isEmpty()) {
            Log.i(TAG, "Global key observed but volume routing is not configured");
            return false;
        }

        if (event.getAction() == KeyEvent.ACTION_DOWN) {
            if (!volumeKeyHeld) {
                AudioManager audio = (AudioManager) getSystemService(AUDIO_SERVICE);
                lockedMediaVolume = audio == null
                        ? -1
                        : audio.getStreamVolume(AudioManager.STREAM_MUSIC);

                volumeKeyHeld = true;
                heldKeyCode = keyCode;
                heldPrefs = prefs;
                heldRemote = remote;
                heldDevice = device;

                mainHandler.removeCallbacks(volumeGuard);
                mainHandler.removeCallbacks(volumeRepeat);
                mainHandler.post(volumeGuard);

                String command = keyCode == KeyEvent.KEYCODE_VOLUME_UP
                        ? "volume_up"
                        : "volume_down";

                // Immediate first step, like a normal remote.
                dispatchVolumeCommand(prefs, remote, device, command);

                // Start local hold-repeat quickly after the initial press.
                mainHandler.postDelayed(volumeRepeat, 280);
            } else if (heldKeyCode != keyCode) {
                // Defensive: if AVA changes direction without a clean UP event,
                // switch the held direction rather than starting a second loop.
                heldKeyCode = keyCode;
            }

        } else if (event.getAction() == KeyEvent.ACTION_UP) {
            volumeKeyHeld = false;
            heldKeyCode = KeyEvent.KEYCODE_UNKNOWN;
            heldPrefs = null;
            heldRemote = "";
            heldDevice = "";

            mainHandler.removeCallbacks(volumeGuard);
            mainHandler.removeCallbacks(volumeRepeat);

            final int restoreVolume = lockedMediaVolume;
            lockedMediaVolume = -1;

            if (restoreVolume >= 0) {
                // AVA's vendor volume handler can run after AccessibilityService.
                // Restore multiple times after release so a late Volume-Up write
                // cannot leave Android media volume changed.
                restoreMediaVolume(restoreVolume, 0);
                restoreMediaVolume(restoreVolume, 40);
                restoreMediaVolume(restoreVolume, 100);
                restoreMediaVolume(restoreVolume, 220);
                restoreMediaVolume(restoreVolume, 450);
            }
        }

        return true;
    }

    private void dispatchVolumeCommand(
            SharedPreferences prefs,
            String remote,
            String device,
            String command
    ) {
        String codeKey = "local_ir_" + command + "_code";
        String code = prefs.getString(codeKey, "");
        int carrier = prefs.getInt("local_ir_carrier_hz", 38000);
        boolean localEnabled = prefs.getBoolean("local_ir_volume_enabled", false);

        if (localEnabled && !code.isEmpty()) {
            try {
                IrBridgeService.transmitBroadlink(this, code, carrier);
                prefs.edit()
                        .putString("global_volume_last_command", command)
                        .putBoolean("global_volume_last_ok", true)
                        .putLong("global_volume_last_time", System.currentTimeMillis())
                        .apply();
                Log.i(TAG, "Local IR volume " + command + " transmitted");
                return;
            } catch (Exception e) {
                Log.e(TAG, "Local IR volume failed; falling back to Apollo server", e);
            }
        }

        sendApolloCommandAsync(prefs, remote, device, command);
    }

    private void restoreMediaVolume(int volume, long delayMs) {
        mainHandler.postDelayed(() -> {
            try {
                AudioManager audio = (AudioManager) getSystemService(AUDIO_SERVICE);
                if (audio != null
                        && audio.getStreamVolume(AudioManager.STREAM_MUSIC) != volume) {
                    audio.setStreamVolume(AudioManager.STREAM_MUSIC, volume, 0);
                }
            } catch (Exception e) {
                Log.w(TAG, "Could not restore AVA media volume", e);
            }
        }, delayMs);
    }

    private void sendApolloCommandAsync(
            SharedPreferences prefs,
            String remote,
            String device,
            String command
    ) {
        final String base = cleanBaseUrl(
                prefs.getString("server_url", "http://homeassistant.local:8100")
        );
        final String apiKey = prefs.getString("api_key", "");

        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("remote_entity_id", remote);
                body.put("device", device);
                body.put("command", command);

                JSONObject response = requestJson(
                        "POST",
                        base + "/api/send",
                        apiKey,
                        body.toString()
                );

                boolean ok = response.optBoolean("ok", false);
                Log.i(TAG, "Volume command " + command + " -> " + device + " ok=" + ok);

                prefs.edit()
                        .putString("global_volume_last_command", command)
                        .putBoolean("global_volume_last_ok", ok)
                        .putLong("global_volume_last_time", System.currentTimeMillis())
                        .apply();

            } catch (Exception e) {
                Log.e(TAG, "Volume command failed: " + command, e);
                prefs.edit()
                        .putString("global_volume_last_command", command)
                        .putBoolean("global_volume_last_ok", false)
                        .putLong("global_volume_last_time", System.currentTimeMillis())
                        .apply();
            }
        }, "apollo-global-volume-" + command).start();
    }

    private static JSONObject requestJson(
            String method,
            String url,
            String authToken,
            String body
    ) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
        connection.setRequestMethod(method);
        connection.setConnectTimeout(2500);
        connection.setReadTimeout(4000);
        connection.setRequestProperty("Accept", "application/json");

        if (authToken != null && !authToken.isEmpty()) {
            connection.setRequestProperty("X-Apollo-IR-Key", authToken);
        }

        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        connection.setDoOutput(true);
        connection.setRequestProperty("Content-Type", "application/json");
        connection.setFixedLengthStreamingMode(bytes.length);

        try (OutputStream out = connection.getOutputStream()) {
            out.write(bytes);
        }

        int code = connection.getResponseCode();
        BufferedReader reader = new BufferedReader(
                new InputStreamReader(
                        code >= 400 ? connection.getErrorStream() : connection.getInputStream(),
                        StandardCharsets.UTF_8
                )
        );

        StringBuilder text = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) text.append(line);
        reader.close();
        connection.disconnect();

        if (code >= 400) {
            throw new IllegalStateException("Server returned HTTP " + code + ": " + text);
        }

        return new JSONObject(text.toString());
    }

    private static String cleanBaseUrl(String value) {
        String cleaned = value == null ? "" : value.trim();
        while (cleaned.endsWith("/")) {
            cleaned = cleaned.substring(0, cleaned.length() - 1);
        }
        return cleaned;
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {}

    @Override
    public void onInterrupt() {
        volumeKeyHeld = false;
        heldKeyCode = KeyEvent.KEYCODE_UNKNOWN;
        heldPrefs = null;
        heldRemote = "";
        heldDevice = "";
        lockedMediaVolume = -1;
        mainHandler.removeCallbacks(volumeGuard);
        mainHandler.removeCallbacks(volumeRepeat);
        Log.w(TAG, "Accessibility service interrupted");
    }

    @Override
    public boolean onUnbind(android.content.Intent intent) {
        volumeKeyHeld = false;
        heldKeyCode = KeyEvent.KEYCODE_UNKNOWN;
        heldPrefs = null;
        heldRemote = "";
        heldDevice = "";
        lockedMediaVolume = -1;
        mainHandler.removeCallbacks(volumeGuard);
        mainHandler.removeCallbacks(volumeRepeat);

        getSharedPreferences(PREFS, MODE_PRIVATE)
                .edit()
                .putBoolean("global_key_service_connected", false)
                .apply();
        return super.onUnbind(intent);
    }
}
