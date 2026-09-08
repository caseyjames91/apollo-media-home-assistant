package com.apollo.avairbridge;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.hardware.ConsumerIrManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
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

    private SharedPreferences prefs;
    private EditText serverUrl;
    private EditText apiKey;
    private Spinner learnerSpinner;
    private Spinner deviceSpinner;
    private EditText commandName;
    private TextView connectionStatus;
    private TextView learnStatus;
    private LinearLayout commandList;
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
        learnerAdapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, learnerLabels);
        learnerAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        learnerSpinner.setAdapter(learnerAdapter);
        learnerCard.addView(learnerSpinner);

        Button refresh = secondaryButton("Refresh learners");
        refresh.setOnClickListener(v -> loadLearners());
        learnerCard.addView(refresh);

        LinearLayout deviceCard = card();
        root.addView(deviceCard);
        deviceCard.addView(sectionTitle("Devices"));
        deviceSpinner = new Spinner(this);
        deviceAdapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, deviceLabels);
        deviceAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        deviceSpinner.setAdapter(deviceAdapter);
        deviceSpinner.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(android.widget.AdapterView<?> parent, View view, int position, long id) {
                renderCommands();
            }
            @Override public void onNothingSelected(android.widget.AdapterView<?> parent) {}
        });
        deviceCard.addView(deviceSpinner);

        Button addExisting = secondaryButton("+ Add existing device");
        addExisting.setOnClickListener(v -> showAddExistingDeviceDialog());
        deviceCard.addView(addExisting);

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
                for (int i = 0; i < arr.length(); i++) {
                    JSONObject item = arr.getJSONObject(i);
                    ids.add(item.getString("id"));
                    labels.add(item.optString("name", item.getString("id")));
                }
                handler.post(() -> {
                    String previous = selectedDeviceId();
                    deviceIds.clear();
                    deviceLabels.clear();
                    deviceIds.addAll(ids);
                    deviceLabels.addAll(labels);
                    deviceAdapter.notifyDataSetChanged();
                    for (int i = 0; i < deviceIds.size(); i++) {
                        if (deviceIds.get(i).equals(previous)) {
                            deviceSpinner.setSelection(i);
                            break;
                        }
                    }
                    renderCommands();
                });
            } catch (Exception e) {
                handler.post(() -> learnStatus.setText("Could not load devices: " + e.getMessage()));
            }
        }, "apollo-devices").start();
    }

    private void showAddExistingDeviceDialog() {
        EditText input = new EditText(this);
        input.setHint("Existing BroadLink device name");
        input.setSingleLine(true);

        new AlertDialog.Builder(this)
                .setTitle("Add existing device")
                .setMessage("Use the same device name already stored in Home Assistant. This does not relearn or modify its existing commands.")
                .setView(input)
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Add", (dialog, which) -> addExistingDevice(input.getText().toString().trim()))
                .show();
    }

    private void addExistingDevice(String device) {
        if (device.isEmpty()) return;
        final String base = cleanBaseUrl(serverUrl.getText().toString());
        final String key = apiKey.getText().toString().trim();

        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("device", device);
                requestJson("POST", base + "/api/devices", key, body.toString());
                handler.post(() -> {
                    learnStatus.setText("Added " + device);
                    loadDevices();
                });
            } catch (Exception e) {
                handler.post(() -> learnStatus.setText("Could not add device: " + e.getMessage()));
            }
        }, "apollo-add-device").start();
    }

    private void renderCommands() {
        if (commandList == null) return;
        commandList.removeAllViews();

        String device = selectedDeviceId();
        if (device.isEmpty()) {
            TextView empty = text("No devices yet. Add an existing device or learn your first command.", 14, false);
            empty.setTextColor(Color.rgb(145, 151, 163));
            commandList.addView(empty);
            return;
        }

        TextView hint = text("Selected: " + device + "\nNew learned commands will be added here automatically.", 14, false);
        hint.setTextColor(Color.rgb(145, 151, 163));
        commandList.addView(hint);
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
                                ? "RF learning active — follow the BroadLink RF sequence."
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
        e.setHintTextColor(Color.rgb(120, 126, 138));
        e.setTextColor(Color.WHITE);
        e.setSingleLine(true);
        e.setTextSize(16);
        e.setPadding(dp(12), dp(10), dp(12), dp(10));
        if (password) {
            e.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        }
        return e;
    }

    private Button primaryButton(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setTextSize(16);
        b.setTextColor(Color.WHITE);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.rgb(80, 96, 230));
        bg.setCornerRadius(dp(14));
        b.setBackground(bg);
        return b;
    }

    private Button secondaryButton(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setTextSize(16);
        b.setTextColor(Color.WHITE);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.rgb(44, 48, 57));
        bg.setCornerRadius(dp(14));
        b.setBackground(bg);
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
