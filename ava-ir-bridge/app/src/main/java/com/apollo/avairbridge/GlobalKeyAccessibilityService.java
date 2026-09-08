package com.apollo.avairbridge;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.content.SharedPreferences;
import android.util.Log;
import android.view.KeyEvent;
import android.view.accessibility.AccessibilityEvent;

public class GlobalKeyAccessibilityService extends AccessibilityService {
    public static final String PREFS = "apollo_ir_bridge";
    public static final String ACTION_KEY_EVENT = "com.apollo.avairbridge.GLOBAL_KEY_EVENT";

    private static final String TAG = "ApolloGlobalKeys";

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

        Log.i(TAG, "Accessibility service connected; global key filtering requested");
    }

    @Override
    public boolean onKeyEvent(KeyEvent event) {
        int keyCode = event.getKeyCode();

        if (keyCode != KeyEvent.KEYCODE_VOLUME_UP
                && keyCode != KeyEvent.KEYCODE_VOLUME_DOWN
                && keyCode != KeyEvent.KEYCODE_VOLUME_MUTE) {
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

        Log.i(TAG, "Global key: " + keyName + " " + actionName);

        android.content.Intent intent = new android.content.Intent(ACTION_KEY_EVENT);
        intent.setPackage(getPackageName());
        intent.putExtra("key", keyName);
        intent.putExtra("action", actionName);
        intent.putExtra("time", timestamp);
        sendBroadcast(intent);

        // Diagnostic only. Let Android/AVA keep normal key behavior.
        return false;
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {}

    @Override
    public void onInterrupt() {
        Log.w(TAG, "Accessibility service interrupted");
    }

    @Override
    public boolean onUnbind(android.content.Intent intent) {
        getSharedPreferences(PREFS, MODE_PRIVATE)
                .edit()
                .putBoolean("global_key_service_connected", false)
                .apply();
        return super.onUnbind(intent);
    }
}
