package com.apollo.avairbridge;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.Dialog;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.hardware.ConsumerIrManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends Activity {
    private static final String PREFS = "apollo_ir_bridge";
    private static final String DEFAULT_SERVER_URL = "http://homeassistant.local:8100";

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final List<String> learnerIds = new ArrayList<>();
    private final List<String> learnerLabels = new ArrayList<>();
    private final List<String> deviceIds = new ArrayList<>();
    private final List<String> deviceLabels = new ArrayList<>();
    private final List<JSONObject> deviceRecords = new ArrayList<>();

    private SharedPreferences prefs;
    private EditText serverUrl;
    private EditText apiKey;
    private Spinner learnerSpinner;
    private Spinner deviceSpinner;
    private EditText commandName;
    private TextView connectionStatus;
    private TextView learnStatus;
    private LinearLayout commandList;
    private TextView deviceEmptyState;
    private EditText commandSearch;
    private ArrayAdapter<String> learnerAdapter;
    private ArrayAdapter<String> deviceAdapter;
    private Button learnIr;
    private Button learnRf;

    private String lastDevice = "";
    private String lastCommand = "";
    private String lastRemote = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(Color.rgb(16, 18, 22));

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(30));
        scroll.addView(root);

        TextView title = text("Apollo Remote", 28, true);
        root.addView(title);

        TextView subtitle = text("IR & RF setup", 15, false);
        subtitle.setTextColor(Color.rgb(150, 156, 168));
        subtitle.setPadding(0, 0, 0, dp(14));
        root.addView(subtitle);

        connectionStatus = badge("Connecting…");
        root.addView(connectionStatus);

        LinearLayout serverCard = card();
        root.addView(serverCard);
        serverCard.addView(sectionTitle("Apollo IR Server"));
        serverUrl = field("Server URL", false);
        apiKey = field("API key (optional)", true);
        serverUrl.setText(prefs.getString("server_url", DEFAULT_SERVER_URL));
        apiKey.setText(prefs.getString("api_key", ""));
        serverCard.addView(serverUrl);
        serverCard.addView(apiKey);

        Button save = primaryButton("Save & Connect");
        save.setOnClickListener(v -> {
            saveSettings();
            refreshAll();
        });
        serverCard.addView(save);

        LinearLayout learnerCard = card();
        root.addView(learnerCard);
        learnerCard.addView(sectionTitle("Learner"));
        learnerSpinner = new Spinner(this);
        learnerAdapter = readableSpinnerAdapter(learnerLabels);
        learnerSpinner.setAdapter(learnerAdapter);
        learnerCard.addView(learnerSpinner);

        Button refresh = secondaryButton("Refresh learners");
        refresh.setOnClickListener(v -> loadLearners());
        learnerCard.addView(refresh);

        LinearLayout deviceCard = card();
        root.addView(deviceCard);
        deviceCard.addView(sectionTitle("Devices"));
        deviceSpinner = new Spinner(this);
        deviceAdapter = readableSpinnerAdapter(deviceLabels);
        deviceSpinner.setAdapter(deviceAdapter);
        deviceSpinner.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(android.widget.AdapterView<?> parent, View view, int position, long id) {
                String selected = selectedDeviceId();
                if (!selected.isEmpty()) {
                    prefs.edit().putString("preferred_device", selected).apply();
                }
                renderCommands();
            }

            @Override public void onNothingSelected(android.widget.AdapterView<?> parent) {}
        });
        deviceCard.addView(deviceSpinner);

        deviceEmptyState = text(
                "Loading devices…",
                13,
                false
        );
        deviceEmptyState.setTextColor(Color.rgb(145, 151, 163));
        deviceEmptyState.setPadding(0, dp(8), 0, dp(10));
        deviceCard.addView(deviceEmptyState);

        LinearLayout deviceActions = new LinearLayout(this);
        deviceActions.setOrientation(LinearLayout.HORIZONTAL);

        Button refreshDevices = secondaryButton("Refresh");
        refreshDevices.setOnClickListener(v -> {
            deviceEmptyState.setText("Refreshing devices…");
            loadDevices();
        });

        Button createDevice = primaryButton("＋ Create");
        createDevice.setOnClickListener(v -> showCreateDeviceDialog(() -> loadDevices()));

        LinearLayout.LayoutParams refreshLp = new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f
        );
        refreshLp.setMargins(0, 0, dp(6), 0);

        LinearLayout.LayoutParams createLp = new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f
        );
        createLp.setMargins(dp(10), 0, 0, 0);

        deviceActions.addView(refreshDevices, refreshLp);
        deviceActions.addView(createDevice, createLp);

        LinearLayout.LayoutParams deviceActionsLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        deviceActionsLp.setMargins(0, dp(4), 0, dp(10));
        deviceCard.addView(deviceActions, deviceActionsLp);

        Button manageDevice = secondaryButton("Manage selected device");
        manageDevice.setOnClickListener(v -> showManageDeviceDialog());
        LinearLayout.LayoutParams manageLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        manageLp.setMargins(0, 0, 0, dp(10));
        deviceCard.addView(manageDevice, manageLp);

        commandSearch = field("Search commands", false);
        commandSearch.setSingleLine(true);
        commandSearch.addTextChangedListener(new android.text.TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence value, int start, int before, int count) {
                renderCommands();
            }
            @Override public void afterTextChanged(android.text.Editable editable) {}
        });
        deviceCard.addView(commandSearch);

        commandList = new LinearLayout(this);
        commandList.setOrientation(LinearLayout.VERTICAL);
        commandList.setPadding(0, dp(8), 0, 0);
        deviceCard.addView(commandList);

        LinearLayout learnCard = card();
        root.addView(learnCard);
        learnCard.addView(sectionTitle("Learn new command"));
        commandName = field("Command name  (power, volume_up, input…)", false);
        learnCard.addView(commandName);

        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);

        learnIr = primaryButton("Learn IR");
        learnRf = secondaryButton("Learn RF");
        LinearLayout.LayoutParams half = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        half.setMargins(0, 0, dp(6), 0);
        row.addView(learnIr, half);
        LinearLayout.LayoutParams half2 = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        half2.setMargins(dp(6), 0, 0, 0);
        row.addView(learnRf, half2);

        learnIr.setOnClickListener(v -> startLearn("ir"));
        learnRf.setOnClickListener(v -> startLearn("rf"));
        learnCard.addView(row);

        learnStatus = text("Ready", 16, false);
        learnStatus.setTextColor(Color.rgb(190, 197, 209));
        learnStatus.setPadding(0, dp(12), 0, 0);
        learnCard.addView(learnStatus);

        setContentView(scroll);
        startBridge();
        refreshAll();
    }

    private void startBridge() {
        Intent i = new Intent(this, IrBridgeService.class);
        if (android.os.Build.VERSION.SDK_INT >= 26) startForegroundService(i);
        else startService(i);
    }

    private void refreshAll() {
        loadLearners();
        loadDevices();
        checkStatus();
    }

    private void saveSettings() {
        prefs.edit()
                .putString("server_url", cleanBaseUrl(serverUrl.getText().toString()))
                .putString("api_key", apiKey.getText().toString().trim())
                .putString("learner", selectedLearnerId())
                .apply();
    }

    private void checkStatus() {
        final String base = cleanBaseUrl(serverUrl.getText().toString());
        final String key = apiKey.getText().toString().trim();
        new Thread(() -> {
            try {
                JSONObject response = requestJson("GET", base + "/status", key, null);
                String version = response.optString("version", "?");
                handler.post(() -> {
                    ConsumerIrManager ir = (ConsumerIrManager) getSystemService(Context.CONSUMER_IR_SERVICE);
                    boolean emitter = ir != null && ir.hasIrEmitter();
                    connectionStatus.setText("● Connected  •  Server " + version + "  •  AVA IR " + (emitter ? "ready" : "unavailable"));
                    connectionStatus.setTextColor(Color.rgb(126, 231, 135));
                });
            } catch (Exception e) {
                handler.post(() -> {
                    connectionStatus.setText("● Offline  •  " + e.getMessage());
                    connectionStatus.setTextColor(Color.rgb(255, 128, 128));
                });
            }
        }, "apollo-status").start();
    }

    private void loadLearners() {
        final String base = cleanBaseUrl(serverUrl.getText().toString());
        final String key = apiKey.getText().toString().trim();
        new Thread(() -> {
            try {
                JSONArray arr = requestJson("GET", base + "/api/learners", key, null).getJSONArray("learners");
                List<String> ids = new ArrayList<>();
                List<String> labels = new ArrayList<>();
                for (int i = 0; i < arr.length(); i++) {
                    JSONObject item = arr.getJSONObject(i);
                    if ("unavailable".equals(item.optString("state"))) continue;
                    String id = item.getString("entity_id");
                    ids.add(id);
                    labels.add(item.optString("name", id));
                }
                handler.post(() -> {
                    String wanted = prefs.getString("learner", "");
                    learnerIds.clear();
                    learnerLabels.clear();
                    learnerIds.addAll(ids);
                    learnerLabels.addAll(labels);
                    learnerAdapter.notifyDataSetChanged();
                    for (int i = 0; i < learnerIds.size(); i++) {
                        if (learnerIds.get(i).equals(wanted)) {
                            learnerSpinner.setSelection(i);
                            break;
                        }
                    }
                });
            } catch (Exception ignored) {}
        }, "apollo-learners").start();
    }

    private void loadDevices() {
        final String base = cleanBaseUrl(serverUrl.getText().toString());
        final String key = apiKey.getText().toString().trim();
        new Thread(() -> {
            try {
                JSONArray arr = requestJson("GET", base + "/api/devices", key, null).getJSONArray("devices");
                List<String> ids = new ArrayList<>();
                List<String> labels = new ArrayList<>();
                List<JSONObject> records = new ArrayList<>();
                for (int i = 0; i < arr.length(); i++) {
                    JSONObject item = arr.getJSONObject(i);
                    String id = item.getString("id");
                    String name = item.optString("name", id);
                    JSONObject commands = item.optJSONObject("commands");
                    int count = commands == null ? 0 : commands.length();
                    String room = item.optString("room", "");
                    ids.add(id);
                    labels.add(
                            name
                                    + " · " + count + (count == 1 ? " command" : " commands")
                                    + (room.isEmpty() ? "" : " · " + room)
                    );
                    records.add(item);
                }

                handler.post(() -> {
                    String previous = selectedDeviceId();
                    deviceIds.clear();
                    deviceLabels.clear();
                    deviceIds.addAll(ids);
                    deviceLabels.addAll(labels);
                    deviceRecords.clear();
                    deviceRecords.addAll(records);
                    deviceAdapter.notifyDataSetChanged();

                    if (deviceIds.isEmpty()) {
                        deviceEmptyState.setText(
                                "No Apollo devices yet. Create your first device below. "
                                        + "Devices learned before Apollo IR Server 0.3.0 are not automatically indexed."
                        );
                    } else {
                        deviceEmptyState.setText(
                                deviceIds.size() + (deviceIds.size() == 1 ? " device" : " devices") + " available"
                        );
                    }

                    String wanted = prefs.getString("preferred_device", previous);
                    boolean selected = false;
                    for (int i = 0; i < deviceIds.size(); i++) {
                        if (deviceIds.get(i).equals(wanted)) {
                            deviceSpinner.setSelection(i);
                            selected = true;
                            break;
                        }
                    }
                    if (!selected && !deviceIds.isEmpty()) {
                        deviceSpinner.setSelection(0);
                    }
                    renderCommands();
                });
            } catch (Exception e) {
                handler.post(() -> {
                    deviceEmptyState.setText("Could not load devices: " + e.getMessage());
                    learnStatus.setText("Could not load devices: " + e.getMessage());
                });
            }
        }, "apollo-devices").start();
    }

    private void showCreateDeviceDialog(Runnable onFinished) {
        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);

        LinearLayout shell = new LinearLayout(this);
        shell.setOrientation(LinearLayout.VERTICAL);
        shell.setPadding(dp(20), dp(20), dp(20), dp(18));

        GradientDrawable shellBg = new GradientDrawable();
        shellBg.setColor(Color.rgb(24, 27, 32));
        shellBg.setCornerRadius(dp(22));
        shellBg.setStroke(dp(1), Color.rgb(50, 55, 65));
        shell.setBackground(shellBg);

        TextView title = text("Create new device", 22, true);
        shell.addView(title);

        TextView subtitle = text(
                "Add a device to Apollo, then teach it IR or RF commands.",
                14,
                false
        );
        subtitle.setTextColor(Color.rgb(155, 162, 174));
        subtitle.setPadding(0, dp(6), 0, dp(14));
        shell.addView(subtitle);

        EditText idField = field("Device ID  (example: bedroom_soundbar)", false);
        EditText nameField = field("Friendly name  (example: Bedroom Soundbar)", false);
        shell.addView(idField);
        shell.addView(nameField);

        TextView idHelp = text(
                "Device ID is the stable key Apollo and Home Assistant will use.",
                12,
                false
        );
        idHelp.setTextColor(Color.rgb(130, 137, 149));
        idHelp.setPadding(dp(2), 0, 0, dp(12));
        shell.addView(idHelp);

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        actions.setPadding(0, dp(8), 0, 0);

        Button cancel = secondaryButton("Cancel");
        Button create = primaryButton("Create Device");

        LinearLayout.LayoutParams cancelLp = new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1f
        );
        cancelLp.setMargins(0, 0, dp(10), 0);

        LinearLayout.LayoutParams createLp = new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1.4f
        );
        createLp.setMargins(dp(6), 0, 0, 0);

        actions.addView(cancel, cancelLp);
        actions.addView(create, createLp);
        shell.addView(actions);

        cancel.setOnClickListener(v -> {
            dialog.dismiss();
            if (onFinished != null) onFinished.run();
        });

        create.setOnClickListener(v -> {
            String device = idField.getText().toString().trim();
            String name = nameField.getText().toString().trim();

            if (device.isEmpty()) {
                idField.setError("Device ID is required");
                return;
            }

            create.setEnabled(false);
            create.setText("Creating…");

            addDevice(
                    device,
                    name.isEmpty() ? null : name,
                    () -> {
                        dialog.dismiss();
                        if (onFinished != null) onFinished.run();
                    }
            );
        });

        dialog.setContentView(shell);
        dialog.setCanceledOnTouchOutside(true);
        dialog.setOnCancelListener(d -> {
            if (onFinished != null) onFinished.run();
        });
        dialog.show();

        Window window = dialog.getWindow();
        if (window != null) {
            window.setBackgroundDrawableResource(android.R.color.transparent);
            int width = getResources().getDisplayMetrics().widthPixels - dp(28);
            window.setLayout(width, LinearLayout.LayoutParams.WRAP_CONTENT);
        }
    }

    private void showManageDeviceDialog() {
        int position = deviceSpinner == null ? -1 : deviceSpinner.getSelectedItemPosition();
        if (position < 0 || position >= deviceRecords.size()) {
            learnStatus.setText("Select a device first.");
            return;
        }

        JSONObject record = deviceRecords.get(position);
        String device = record.optString("id", "");
        String name = record.optString("name", device);
        String room = record.optString("room", "");
        JSONObject commands = record.optJSONObject("commands");
        int commandCount = commands == null ? 0 : commands.length();

        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);

        LinearLayout shell = new LinearLayout(this);
        shell.setOrientation(LinearLayout.VERTICAL);
        shell.setPadding(dp(20), dp(20), dp(20), dp(18));

        GradientDrawable shellBg = new GradientDrawable();
        shellBg.setColor(Color.rgb(24, 27, 32));
        shellBg.setCornerRadius(dp(22));
        shellBg.setStroke(dp(1), Color.rgb(50, 55, 65));
        shell.setBackground(shellBg);

        TextView title = text(name, 22, true);
        shell.addView(title);

        TextView meta = text(
                device + " · " + commandCount + (commandCount == 1 ? " command" : " commands"),
                13,
                false
        );
        meta.setTextColor(Color.rgb(145, 151, 163));
        meta.setPadding(0, dp(4), 0, dp(12));
        shell.addView(meta);

        EditText roomField = field("Room (optional)", false);
        roomField.setText(room);
        LinearLayout.LayoutParams roomLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        roomLp.setMargins(0, dp(4), 0, dp(10));
        roomField.setLayoutParams(roomLp);
        shell.addView(roomField);

        Button saveRoom = primaryButton("Save room");
        saveRoom.setOnClickListener(v -> {
            setDeviceRoom(device, roomField.getText().toString().trim());
            dialog.dismiss();
        });
        LinearLayout.LayoutParams saveRoomLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        saveRoomLp.setMargins(0, 0, 0, dp(10));
        shell.addView(saveRoom, saveRoomLp);

        Button deleteDevice = secondaryButton(
                commandCount == 0 ? "Delete device" : "Delete device & all commands"
        );
        deleteDevice.setOnClickListener(v -> {
            dialog.dismiss();
            String remote = selectedLearnerId();
            showConfirmDialog(
                    "Delete device?",
                    commandCount == 0
                            ? "Delete " + name + " from Apollo?"
                            : "Delete " + name + " and all " + commandCount
                                    + " commands from Home Assistant/BroadLink and Apollo?",
                    "Delete",
                    () -> deleteDevice(remote, device, commandCount > 0)
            );
        });
        LinearLayout.LayoutParams deleteDeviceLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        deleteDeviceLp.setMargins(0, 0, 0, dp(10));
        shell.addView(deleteDevice, deleteDeviceLp);

        Button close = secondaryButton("Close");
        close.setOnClickListener(v -> dialog.dismiss());
        shell.addView(close);

        dialog.setContentView(shell);
        dialog.show();

        Window window = dialog.getWindow();
        if (window != null) {
            window.setBackgroundDrawableResource(android.R.color.transparent);
            int width = getResources().getDisplayMetrics().widthPixels - dp(28);
            window.setLayout(width, LinearLayout.LayoutParams.WRAP_CONTENT);
        }
    }

    private void setDeviceRoom(String device, String room) {
        final String base = cleanBaseUrl(serverUrl.getText().toString());
        final String key = apiKey.getText().toString().trim();

        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("device", device);
                body.put("room", room);
                requestJson("POST", base + "/api/devices/room", key, body.toString());

                handler.post(() -> {
                    learnStatus.setText(room.isEmpty() ? "✓ Room cleared" : "✓ Assigned to " + room);
                    loadDevices();
                });
            } catch (Exception e) {
                handler.post(() -> learnStatus.setText("Room update failed: " + e.getMessage()));
            }
        }, "apollo-device-room").start();
    }

    private void deleteDevice(String remote, String device, boolean deleteCommands) {
        if (deleteCommands && (remote == null || remote.isEmpty())) {
            learnStatus.setText("Choose the BroadLink learner before deleting this device.");
            return;
        }

        final String base = cleanBaseUrl(serverUrl.getText().toString());
        final String key = apiKey.getText().toString().trim();

        learnStatus.setText("Deleting device…");

        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("device", device);
                body.put("delete_commands", deleteCommands);
                if (remote != null && !remote.isEmpty()) {
                    body.put("remote_entity_id", remote);
                }

                requestJson("POST", base + "/api/devices/delete", key, body.toString());

                handler.post(() -> {
                    learnStatus.setText("✓ Device deleted");
                    prefs.edit().remove("preferred_device").apply();
                    loadDevices();
                });
            } catch (Exception e) {
                handler.post(() -> learnStatus.setText("Device delete failed: " + e.getMessage()));
            }
        }, "apollo-delete-device").start();
    }

    private void showConfirmDialog(
            String titleText,
            String messageText,
            String confirmText,
            Runnable onConfirm
    ) {
        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);

        LinearLayout shell = new LinearLayout(this);
        shell.setOrientation(LinearLayout.VERTICAL);
        shell.setPadding(dp(20), dp(20), dp(20), dp(18));

        GradientDrawable shellBg = new GradientDrawable();
        shellBg.setColor(Color.rgb(24, 27, 32));
        shellBg.setCornerRadius(dp(22));
        shellBg.setStroke(dp(1), Color.rgb(50, 55, 65));
        shell.setBackground(shellBg);

        TextView title = text(titleText, 21, true);
        shell.addView(title);

        TextView message = text(messageText, 14, false);
        message.setTextColor(Color.rgb(165, 171, 183));
        message.setPadding(0, dp(8), 0, dp(16));
        shell.addView(message);

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);

        Button cancel = secondaryButton("Cancel");
        Button confirm = primaryButton(confirmText);

        LinearLayout.LayoutParams left = new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f
        );
        left.setMargins(0, 0, dp(8), 0);

        LinearLayout.LayoutParams right = new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f
        );
        right.setMargins(dp(8), 0, 0, 0);

        actions.addView(cancel, left);
        actions.addView(confirm, right);
        shell.addView(actions);

        cancel.setOnClickListener(v -> dialog.dismiss());
        confirm.setOnClickListener(v -> {
            dialog.dismiss();
            onConfirm.run();
        });

        dialog.setContentView(shell);
        dialog.show();

        Window window = dialog.getWindow();
        if (window != null) {
            window.setBackgroundDrawableResource(android.R.color.transparent);
            int width = getResources().getDisplayMetrics().widthPixels - dp(28);
            window.setLayout(width, LinearLayout.LayoutParams.WRAP_CONTENT);
        }
    }

    private void addDevice(String device, String displayName, Runnable onFinished) {
        final String base = cleanBaseUrl(serverUrl.getText().toString());
        final String key = apiKey.getText().toString().trim();

        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("device", device);
                if (displayName != null && !displayName.isEmpty()) {
                    body.put("name", displayName);
                }

                requestJson("POST", base + "/api/devices", key, body.toString());

                handler.post(() -> {
                    prefs.edit().putString("preferred_device", device).apply();
                    learnStatus.setText("✓ Device ready: " + (displayName == null ? device : displayName));
                    if (onFinished != null) onFinished.run();
                });
            } catch (Exception e) {
                handler.post(() -> {
                    learnStatus.setText("Could not add device: " + e.getMessage());
                    if (onFinished != null) onFinished.run();
                });
            }
        }, "apollo-add-device").start();
    }

    private void renderCommands() {
        if (commandList == null) return;
        commandList.removeAllViews();

        int position = deviceSpinner == null ? -1 : deviceSpinner.getSelectedItemPosition();
        if (position < 0 || position >= deviceRecords.size()) {
            TextView empty = text("No device selected.", 14, false);
            empty.setTextColor(Color.rgb(145, 151, 163));
            commandList.addView(empty);
            return;
        }

        JSONObject deviceRecord = deviceRecords.get(position);
        String deviceId = deviceRecord.optString("id", selectedDeviceId());
        JSONObject commands = deviceRecord.optJSONObject("commands");

        String query = commandSearch == null
                ? ""
                : commandSearch.getText().toString().trim().toLowerCase();

        TextView heading = text("Commands", 16, true);
        heading.setPadding(0, dp(10), 0, dp(6));
        commandList.addView(heading);

        if (commands == null || commands.length() == 0) {
            TextView empty = text(
                    "No commands learned yet. Use Learn new command below.",
                    14,
                    false
            );
            empty.setTextColor(Color.rgb(145, 151, 163));
            commandList.addView(empty);
            return;
        }

        JSONArray names = commands.names();
        if (names == null) return;

        int shown = 0;

        for (int i = 0; i < names.length(); i++) {
            String command = names.optString(i, "");
            if (command.isEmpty()) continue;
            if (!query.isEmpty() && !command.toLowerCase().contains(query)) continue;

            JSONObject meta = commands.optJSONObject(command);
            String type = meta == null ? "" : meta.optString("type", "");
            String learnerEntity = meta == null ? "" : meta.optString("learner_entity_id", "");
            String learnedAt = meta == null ? "" : meta.optString("learned_at", "");
            String lastUsedAt = meta == null ? "" : meta.optString("last_used_at", "");

            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(dp(12), dp(10), dp(8), dp(10));

            GradientDrawable rowBg = new GradientDrawable();
            rowBg.setColor(Color.rgb(32, 35, 42));
            rowBg.setCornerRadius(dp(12));
            row.setBackground(rowBg);

            LinearLayout.LayoutParams rowLp = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
            );
            rowLp.setMargins(0, dp(5), 0, dp(5));
            row.setLayoutParams(rowLp);

            LinearLayout labels = new LinearLayout(this);
            labels.setOrientation(LinearLayout.VERTICAL);

            TextView nameView = text(command, 16, true);
            labels.addView(nameView);

            String metaText = type.isEmpty() ? "Learned command" : type.toUpperCase() + " command";
            if (!lastUsedAt.isEmpty() && !"null".equals(lastUsedAt)) {
                metaText += " · used";
            } else if (!learnedAt.isEmpty()) {
                metaText += " · learned";
            }

            TextView typeView = text(metaText, 12, false);
            typeView.setTextColor(Color.rgb(135, 142, 154));
            labels.addView(typeView);

            LinearLayout.LayoutParams labelsLp = new LinearLayout.LayoutParams(
                    0,
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    1f
            );
            row.addView(labels, labelsLp);

            ImageButton test = iconButton(
                    R.drawable.ic_apollo_play,
                    "Test " + command
            );
            test.setOnClickListener(v ->
                    sendCommandFromBrowser(test, learnerEntity, deviceId, command)
            );

            LinearLayout.LayoutParams testLp = new LinearLayout.LayoutParams(
                    dp(52),
                    dp(48)
            );
            testLp.setMargins(0, 0, dp(8), 0);
            row.addView(test, testLp);

            ImageButton delete = iconButton(
                    R.drawable.ic_apollo_delete,
                    "Delete " + command
            );
            delete.setOnClickListener(v ->
                    showDeleteCommandDialog(learnerEntity, deviceId, command)
            );

            LinearLayout.LayoutParams deleteLp = new LinearLayout.LayoutParams(
                    dp(52),
                    dp(48)
            );
            row.addView(delete, deleteLp);

            commandList.addView(row);
            shown++;
        }

        if (shown == 0) {
            TextView empty = text("No commands match your search.", 14, false);
            empty.setTextColor(Color.rgb(145, 151, 163));
            commandList.addView(empty);
        }
    }

    private void showDeleteCommandDialog(
            String storedRemote,
            String device,
            String command
    ) {
        String remote = storedRemote == null || storedRemote.isEmpty()
                ? selectedLearnerId()
                : storedRemote;

        if (remote == null || remote.isEmpty()) {
            learnStatus.setText("Choose the BroadLink learner before deleting this command.");
            return;
        }

        final String deleteRemote = remote;

        showConfirmDialog(
                "Delete command?",
                device + " · " + command + "\n\nThis removes it from Home Assistant/BroadLink and Apollo.",
                "Delete",
                () -> deleteCommand(deleteRemote, device, command)
        );
    }

    private void deleteCommand(String remote, String device, String command) {
        final String base = cleanBaseUrl(serverUrl.getText().toString());
        final String key = apiKey.getText().toString().trim();

        learnStatus.setText("Deleting " + command + "…");

        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("remote_entity_id", remote);
                body.put("device", device);
                body.put("command", command);

                requestJson("POST", base + "/api/commands/delete", key, body.toString());

                handler.post(() -> {
                    learnStatus.setText("✓ Deleted  " + device + " · " + command);
                    loadDevices();
                });
            } catch (Exception e) {
                handler.post(() -> learnStatus.setText("Delete failed: " + e.getMessage()));
            }
        }, "apollo-delete-command").start();
    }

    private void sendCommandFromBrowser(
            View button,
            String storedRemote,
            String device,
            String command
    ) {
        String remote = storedRemote;
        if (remote == null || remote.isEmpty()) {
            remote = selectedLearnerId();
        }

        if (remote == null || remote.isEmpty()) {
            learnStatus.setText("Choose a learner before testing this command.");
            return;
        }

        final String sendRemote = remote;
        final String base = cleanBaseUrl(serverUrl.getText().toString());
        final String key = apiKey.getText().toString().trim();

        button.setEnabled(false);
        button.setAlpha(0.55f);
        learnStatus.setText("Sending " + command + "…");

        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("remote_entity_id", sendRemote);
                body.put("device", device);
                body.put("command", command);

                requestJson("POST", base + "/api/send", key, body.toString());

                handler.post(() -> {
                    learnStatus.setText("✓ Sent  " + device + " · " + command);
                    button.setAlpha(1f);
                    button.setEnabled(true);
                });
            } catch (Exception e) {
                handler.post(() -> {
                    learnStatus.setText("Test failed: " + e.getMessage());
                    button.setAlpha(1f);
                    button.setEnabled(true);
                });
            }
        }, "apollo-command-test").start();
    }

    private void startLearn(String type) {
        saveSettings();

        final String base = cleanBaseUrl(serverUrl.getText().toString());
        final String key = apiKey.getText().toString().trim();
        final String remote = selectedLearnerId();
        final String device = selectedDeviceId();
        final String command = commandName.getText().toString().trim();

        if (remote.isEmpty()) {
            learnStatus.setText("Choose a learner first.");
            return;
        }
        if (device.isEmpty()) {
            learnStatus.setText("Choose or add a device first.");
            return;
        }
        if (command.isEmpty()) {
            learnStatus.setText("Enter a command name.");
            return;
        }

        setLearning(true);
        learnStatus.setText(type.equals("rf") ? "Starting RF learning…" : "Starting IR learning…");

        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("learner_entity_id", remote);
                body.put("device", device);
                body.put("command", command);
                body.put("command_type", type);
                body.put("timeout", type.equals("rf") ? 45 : 30);

                JSONObject response = requestJson("POST", base + "/api/learn", key, body.toString());
                String id = response.getString("id");

                handler.post(() -> learnStatus.setText(
                        type.equals("rf")
                                ? "RF learning active — hold/press the original remote near BroadLink. "
                                        + "If BroadLink requests another press, press it again."
                                : "IR learning active — point the original remote at BroadLink and press the button."
                ));

                pollJob(base, key, id, remote, device, command);
            } catch (Exception e) {
                handler.post(() -> {
                    learnStatus.setText("Could not start learning: " + e.getMessage());
                    setLearning(false);
                });
            }
        }, "apollo-learn").start();
    }

    private void pollJob(String base, String key, String id, String remote, String device, String command) {
        new Thread(() -> {
            try {
                while (true) {
                    Thread.sleep(900);
                    JSONObject job = requestJson("GET", base + "/api/jobs/" + id, key, null);
                    String state = job.optString("state", "unknown");
                    String message = job.optString("message", state);

                    if ("learned".equals(state)) {
                        lastRemote = remote;
                        lastDevice = device;
                        lastCommand = command;
                        handler.post(() -> {
                            learnStatus.setText("✓ Learned  " + command);
                            commandName.setText("");
                            setLearning(false);
                            loadDevices();
                            showLearnedDialog();
                        });
                        return;
                    }

                    if ("timeout".equals(state) || "error".equals(state) || "cancelled".equals(state)) {
                        handler.post(() -> {
                            learnStatus.setText("Learning failed: " + message);
                            setLearning(false);
                        });
                        return;
                    }

                    handler.post(() -> learnStatus.setText(message));
                }
            } catch (Exception e) {
                handler.post(() -> {
                    learnStatus.setText("Lost learning status: " + e.getMessage());
                    setLearning(false);
                });
            }
        }, "apollo-job").start();
    }

    private void showLearnedDialog() {
        new AlertDialog.Builder(this)
                .setTitle("Command learned")
                .setMessage(lastDevice + "  •  " + lastCommand)
                .setNegativeButton("Done", null)
                .setPositiveButton("Test", (dialog, which) -> sendTest())
                .show();
    }

    private void sendTest() {
        if (lastRemote.isEmpty() || lastDevice.isEmpty() || lastCommand.isEmpty()) return;
        final String base = cleanBaseUrl(serverUrl.getText().toString());
        final String key = apiKey.getText().toString().trim();

        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("remote_entity_id", lastRemote);
                body.put("device", lastDevice);
                body.put("command", lastCommand);
                requestJson("POST", base + "/api/send", key, body.toString());
                handler.post(() -> learnStatus.setText("✓ Test sent"));
            } catch (Exception e) {
                handler.post(() -> learnStatus.setText("Test failed: " + e.getMessage()));
            }
        }, "apollo-test").start();
    }

    private void setLearning(boolean busy) {
        learnIr.setEnabled(!busy);
        learnRf.setEnabled(!busy);
        learnerSpinner.setEnabled(!busy);
        deviceSpinner.setEnabled(!busy);
        commandName.setEnabled(!busy);
    }

    private String selectedLearnerId() {
        int p = learnerSpinner == null ? -1 : learnerSpinner.getSelectedItemPosition();
        return p >= 0 && p < learnerIds.size() ? learnerIds.get(p) : "";
    }

    private String selectedDeviceId() {
        int p = deviceSpinner == null ? -1 : deviceSpinner.getSelectedItemPosition();
        return p >= 0 && p < deviceIds.size() ? deviceIds.get(p) : "";
    }

    private ArrayAdapter<String> readableSpinnerAdapter(List<String> items) {
        return new ArrayAdapter<String>(this, android.R.layout.simple_spinner_item, items) {
            @Override
            public View getView(int position, View convertView, ViewGroup parent) {
                TextView view = (TextView) super.getView(position, convertView, parent);
                styleSpinnerText(view, false);
                return view;
            }

            @Override
            public View getDropDownView(int position, View convertView, ViewGroup parent) {
                TextView view = (TextView) super.getDropDownView(position, convertView, parent);
                styleSpinnerText(view, true);
                return view;
            }
        };
    }

    private void styleSpinnerText(TextView view, boolean dropdown) {
        view.setTextColor(Color.WHITE);
        view.setTextSize(16);
        view.setPadding(dp(12), dp(12), dp(12), dp(12));

        if (dropdown) {
            view.setBackgroundColor(Color.rgb(35, 39, 47));
        } else {
            GradientDrawable bg = new GradientDrawable();
            bg.setColor(Color.rgb(31, 34, 41));
            bg.setCornerRadius(dp(12));
            view.setBackground(bg);
        }
    }

    private JSONObject requestJson(String method, String url, String authToken, String body) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
        connection.setRequestMethod(method);
        connection.setConnectTimeout(5000);
        connection.setReadTimeout(7000);

        if (authToken != null && !authToken.isEmpty()) {
            connection.setRequestProperty("X-Apollo-IR-Key", authToken);
        }
        connection.setRequestProperty("Accept", "application/json");

        if (body != null) {
            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json");
            connection.setFixedLengthStreamingMode(bytes.length);
            try (OutputStream out = connection.getOutputStream()) {
                out.write(bytes);
            }
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

    private String cleanBaseUrl(String value) {
        String cleaned = value.trim();
        while (cleaned.endsWith("/")) cleaned = cleaned.substring(0, cleaned.length() - 1);
        return cleaned;
    }

    private LinearLayout card() {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(16), dp(14), dp(16), dp(16));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        lp.setMargins(0, dp(12), 0, 0);
        card.setLayoutParams(lp);

        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.rgb(27, 30, 36));
        bg.setCornerRadius(dp(18));
        bg.setStroke(dp(1), Color.rgb(48, 52, 61));
        card.setBackground(bg);
        return card;
    }

    private TextView sectionTitle(String value) {
        TextView t = text(value, 18, true);
        t.setPadding(0, 0, 0, dp(10));
        return t;
    }

    private TextView badge(String value) {
        TextView t = text(value, 14, true);
        t.setPadding(dp(12), dp(8), dp(12), dp(8));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.rgb(29, 37, 33));
        bg.setCornerRadius(dp(40));
        t.setBackground(bg);
        return t;
    }

    private EditText field(String hint, boolean password) {
        EditText e = new EditText(this);
        e.setHint(hint);
        e.setHintTextColor(Color.rgb(150, 156, 168));
        e.setTextColor(Color.WHITE);
        e.setSingleLine(true);
        e.setTextSize(16);
        e.setPadding(dp(12), dp(10), dp(12), dp(10));

        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.rgb(34, 37, 44));
        bg.setCornerRadius(dp(12));
        bg.setStroke(dp(1), Color.rgb(58, 63, 74));
        e.setBackground(bg);

        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        lp.setMargins(0, dp(6), 0, dp(6));
        e.setLayoutParams(lp);

        if (password) {
            e.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        }
        return e;
    }

    private ImageButton iconButton(int drawableRes, String description) {
        ImageButton button = new ImageButton(this);
        button.setImageResource(drawableRes);
        button.setContentDescription(description);
        button.setPadding(dp(12), dp(12), dp(12), dp(12));

        GradientDrawable content = new GradientDrawable();
        content.setColor(Color.rgb(44, 48, 57));
        content.setCornerRadius(dp(14));

        RippleDrawable ripple = new RippleDrawable(
                ColorStateList.valueOf(Color.argb(70, 255, 255, 255)),
                content,
                null
        );
        button.setBackground(ripple);

        button.setOnTouchListener((view, event) -> {
            switch (event.getActionMasked()) {
                case android.view.MotionEvent.ACTION_DOWN:
                    view.setScaleX(0.96f);
                    view.setScaleY(0.96f);
                    break;
                case android.view.MotionEvent.ACTION_UP:
                case android.view.MotionEvent.ACTION_CANCEL:
                    view.animate().scaleX(1f).scaleY(1f).setDuration(90).start();
                    break;
                default:
                    break;
            }
            return false;
        });

        return button;
    }

    private Button primaryButton(String label) {
        return styledButton(label, Color.rgb(80, 96, 230), Color.argb(90, 255, 255, 255));
    }

    private Button secondaryButton(String label) {
        return styledButton(label, Color.rgb(44, 48, 57), Color.argb(70, 255, 255, 255));
    }

    private Button styledButton(String label, int backgroundColor, int rippleColor) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setTextSize(16);
        b.setTextColor(Color.WHITE);
        b.setPadding(dp(14), dp(10), dp(14), dp(10));

        GradientDrawable content = new GradientDrawable();
        content.setColor(backgroundColor);
        content.setCornerRadius(dp(14));

        RippleDrawable ripple = new RippleDrawable(
                ColorStateList.valueOf(rippleColor),
                content,
                null
        );
        b.setBackground(ripple);

        // Subtle physical press feedback in addition to the ripple.
        b.setOnTouchListener((view, event) -> {
            switch (event.getActionMasked()) {
                case android.view.MotionEvent.ACTION_DOWN:
                    view.setScaleX(0.98f);
                    view.setScaleY(0.98f);
                    break;
                case android.view.MotionEvent.ACTION_UP:
                case android.view.MotionEvent.ACTION_CANCEL:
                    view.animate().scaleX(1f).scaleY(1f).setDuration(90).start();
                    break;
                default:
                    break;
            }
            return false;
        });

        return b;
    }

    private TextView text(String value, int size, boolean bold) {
        TextView t = new TextView(this);
        t.setText(value);
        t.setTextSize(size);
        t.setTextColor(Color.WHITE);
        if (bold) t.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return t;
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density);
    }
}
