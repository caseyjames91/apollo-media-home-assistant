package com.apollo.avairbridge;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.hardware.ConsumerIrManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
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

    private TextView status;
    private TextView learnStatus;
    private TextView selectedLearnerLabel;
    private EditText serverUrl;
    private EditText apiKey;
    private EditText deviceName;
    private EditText commandName;
    private Spinner learnerSpinner;
    private Button refreshLearners;
    private Button learnIr;
    private Button learnRf;
    private Button testLast;

    private final List<String> learnerIds = new ArrayList<>();
    private final List<String> learnerLabels = new ArrayList<>();
    private ArrayAdapter<String> learnerAdapter;

    private SharedPreferences prefs;

    private String lastDevice = "";
    private String lastCommand = "";
    private String lastRemote = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);

        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int p = dp(18);
        root.setPadding(p, p, p, p);
        scroll.addView(root);

        TextView title = new TextView(this);
        title.setText("Apollo AVA Bridge 0.7.0");
        title.setTextSize(24);
        root.addView(title);

        status = new TextView(this);
        status.setTextSize(14);
        status.setPadding(0, dp(8), 0, dp(12));
        root.addView(status);

        addSection(root, "Apollo IR Server");

        serverUrl = addField(root, "Apollo IR Server URL", false);
        apiKey = addField(root, "Apollo IR API key (optional)", true);
        serverUrl.setText(prefs.getString("server_url",
                prefs.getString("ha_url", DEFAULT_SERVER_URL)));
        apiKey.setText(prefs.getString("api_key",
                prefs.getString("ha_token", "")));

        Button save = new Button(this);
        save.setText("Save Server Settings");
        save.setOnClickListener(v -> {
            saveSettings();
            loadLearners();
        });
        root.addView(save);

        addSection(root, "IR / RF Learner");

        learnerSpinner = new Spinner(this);
        learnerAdapter = new ArrayAdapter<>(
                this,
                android.R.layout.simple_spinner_item,
                learnerLabels
        );
        learnerAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        learnerSpinner.setAdapter(learnerAdapter);
        root.addView(learnerSpinner);

        selectedLearnerLabel = new TextView(this);
        selectedLearnerLabel.setText("Loading Home Assistant remote entities…");
        selectedLearnerLabel.setPadding(0, dp(6), 0, dp(6));
        root.addView(selectedLearnerLabel);

        refreshLearners = new Button(this);
        refreshLearners.setText("Refresh Learners");
        refreshLearners.setOnClickListener(v -> loadLearners());
        root.addView(refreshLearners);

        addSection(root, "Learn a command");

        deviceName = addField(root, "Device name (example: bedroom_ped_fan)", false);
        commandName = addField(root, "Command name (example: power)", false);

        learnIr = new Button(this);
        learnIr.setText("Learn IR");
        learnIr.setOnClickListener(v -> startLearn("ir"));
        root.addView(learnIr);

        learnRf = new Button(this);
        learnRf.setText("Learn RF");
        learnRf.setOnClickListener(v -> startLearn("rf"));
        root.addView(learnRf);

        learnStatus = new TextView(this);
        learnStatus.setText("Ready.");
        learnStatus.setTextSize(18);
        learnStatus.setPadding(0, dp(14), 0, dp(10));
        root.addView(learnStatus);

        testLast = new Button(this);
        testLast.setText("Test Last Learned Command");
        testLast.setEnabled(false);
        testLast.setVisibility(View.GONE);
        testLast.setOnClickListener(v -> testLastLearned());
        root.addView(testLast);

        TextView note = new TextView(this);
        note.setText(
                "BroadLink performs learning through Home Assistant. "
                        + "AVA provides the setup UI and room-local IR emitter."
        );
        note.setPadding(0, dp(10), 0, dp(12));
        root.addView(note);

        setContentView(scroll);
        startBridge();
        refreshStatus();
        loadLearners();
    }

    private void addSection(LinearLayout root, String text) {
        TextView section = new TextView(this);
        section.setText(text);
        section.setTextSize(20);
        section.setPadding(0, dp(18), 0, dp(6));
        root.addView(section);
    }

    private EditText addField(LinearLayout root, String hint, boolean password) {
        EditText field = new EditText(this);
        field.setHint(hint);
        field.setTextSize(16);
        field.setSingleLine(true);
        if (password) {
            field.setInputType(
                    InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD
            );
        }
        root.addView(field);
        return field;
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density);
    }

    private void startBridge() {
        Intent i = new Intent(this, IrBridgeService.class);
        if (android.os.Build.VERSION.SDK_INT >= 26) {
            startForegroundService(i);
        } else {
            startService(i);
        }
        refreshStatus();
    }

    private void saveSettings() {
        String selected = selectedLearnerId();
        prefs.edit()
                .putString("server_url", cleanBaseUrl(serverUrl.getText().toString()))
                .putString("api_key", apiKey.getText().toString().trim())
                .putString("learner", selected)
                .apply();
    }

    private String selectedLearnerId() {
        int position = learnerSpinner.getSelectedItemPosition();
        if (position >= 0 && position < learnerIds.size()) {
            return learnerIds.get(position);
        }
        return "";
    }

    private void loadLearners() {
        final String base = cleanBaseUrl(serverUrl.getText().toString());
        final String key = apiKey.getText().toString().trim();

        if (base.isEmpty()) {
            selectedLearnerLabel.setText("Enter the Apollo IR Server URL first.");
            return;
        }

        refreshLearners.setEnabled(false);
        selectedLearnerLabel.setText("Finding Home Assistant remote entities…");

        new Thread(() -> {
            try {
                JSONObject response = requestJson(
                        "GET",
                        base + "/api/learners",
                        key,
                        null
                );
                JSONArray learners = response.getJSONArray("learners");

                List<String> ids = new ArrayList<>();
                List<String> labels = new ArrayList<>();

                for (int i = 0; i < learners.length(); i++) {
                    JSONObject item = learners.getJSONObject(i);
                    String id = item.getString("entity_id");
                    String name = item.optString("name", id);
                    String state = item.optString("state", "");
                    ids.add(id);
                    labels.add(name + "  (" + id + ")" + ("unavailable".equals(state) ? " — unavailable" : ""));
                }

                handler.post(() -> {
                    String wanted = prefs.getString("learner", "");
                    learnerIds.clear();
                    learnerLabels.clear();
                    learnerIds.addAll(ids);
                    learnerLabels.addAll(labels);
                    learnerAdapter.notifyDataSetChanged();

                    int select = 0;
                    for (int i = 0; i < learnerIds.size(); i++) {
                        if (learnerIds.get(i).equals(wanted)) {
                            select = i;
                            break;
                        }
                    }
                    if (!learnerIds.isEmpty()) {
                        learnerSpinner.setSelection(select);
                        selectedLearnerLabel.setText(
                                learnerIds.size() + " remote entities found. Select the BroadLink learner."
                        );
                    } else {
                        selectedLearnerLabel.setText("No remote entities found.");
                    }
                    refreshLearners.setEnabled(true);
                });
            } catch (Exception e) {
                handler.post(() -> {
                    selectedLearnerLabel.setText("Could not load learners: " + e.getMessage());
                    refreshLearners.setEnabled(true);
                });
            }
        }, "apollo-load-learners").start();
    }

    private void setLearning(boolean busy) {
        learnIr.setEnabled(!busy);
        learnRf.setEnabled(!busy);
        deviceName.setEnabled(!busy);
        commandName.setEnabled(!busy);
        learnerSpinner.setEnabled(!busy);
        refreshLearners.setEnabled(!busy);
        testLast.setEnabled(!busy && !lastCommand.isEmpty());
    }

    private void startLearn(String type) {
        saveSettings();

        String base = cleanBaseUrl(serverUrl.getText().toString());
        String key = apiKey.getText().toString().trim();
        String remote = selectedLearnerId();
        String device = deviceName.getText().toString().trim();
        String command = commandName.getText().toString().trim();

        if (base.isEmpty() || remote.isEmpty()) {
            learnStatus.setText("Select an Apollo IR Server and learner first.");
            return;
        }
        if (device.isEmpty() || command.isEmpty()) {
            learnStatus.setText("Enter both a device name and command name.");
            return;
        }

        setLearning(true);
        testLast.setVisibility(View.GONE);
        learnStatus.setText(
                type.equals("rf")
                        ? "Starting RF learning…"
                        : "Starting IR learning…"
        );

        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("learner_entity_id", remote);
                body.put("device", device);
                body.put("command", command);
                body.put("command_type", type);
                body.put("timeout", type.equals("rf") ? 45 : 30);

                JSONObject response = requestJson(
                        "POST",
                        base + "/api/learn",
                        key,
                        body.toString()
                );

                String id = response.getString("id");
                handler.post(() -> learnStatus.setText(
                        type.equals("rf")
                                ? "RF learning active\nFollow the BroadLink RF learning sequence with the original remote."
                                : "IR learning active\nPoint the original remote at the BroadLink and press the button."
                ));
                pollJob(base, key, id, remote, device, command);
            } catch (Exception e) {
                handler.post(() -> {
                    learnStatus.setText("Could not start learning\n" + e.getMessage());
                    setLearning(false);
                });
            }
        }, "apollo-learn").start();
    }

    private void pollJob(
            String base,
            String key,
            String id,
            String remote,
            String device,
            String command
    ) {
        new Thread(() -> {
            try {
                while (true) {
                    Thread.sleep(900);
                    JSONObject job = requestJson(
                            "GET",
                            base + "/api/jobs/" + id,
                            key,
                            null
                    );

                    String state = job.optString("state", "unknown");
                    String message = job.optString("message", state);

                    handler.post(() -> learnStatus.setText(message));

                    if (state.equals("learned")) {
                        lastRemote = remote;
                        lastDevice = device;
                        lastCommand = command;
                        handler.post(() -> {
                            learnStatus.setText(
                                    "✓ Learned\n" + device + " · " + command
                            );
                            testLast.setVisibility(View.VISIBLE);
                            testLast.setEnabled(true);
                            setLearning(false);
                        });
                        return;
                    }

                    if (state.equals("timeout")
                            || state.equals("error")
                            || state.equals("cancelled")) {
                        handler.post(() -> {
                            learnStatus.setText("Learning failed\n" + message);
                            setLearning(false);
                        });
                        return;
                    }
                }
            } catch (Exception e) {
                handler.post(() -> {
                    learnStatus.setText("Lost learning status\n" + e.getMessage());
                    setLearning(false);
                });
            }
        }, "apollo-job").start();
    }

    private void testLastLearned() {
        if (lastRemote.isEmpty() || lastDevice.isEmpty() || lastCommand.isEmpty()) {
            return;
        }

        final String base = cleanBaseUrl(serverUrl.getText().toString());
        final String key = apiKey.getText().toString().trim();

        testLast.setEnabled(false);
        learnStatus.setText("Sending test command…");

        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("remote_entity_id", lastRemote);
                body.put("device", lastDevice);
                body.put("command", lastCommand);

                requestJson(
                        "POST",
                        base + "/api/send",
                        key,
                        body.toString()
                );

                handler.post(() -> {
                    learnStatus.setText("✓ Test command sent\n" + lastDevice + " · " + lastCommand);
                    testLast.setEnabled(true);
                });
            } catch (Exception e) {
                handler.post(() -> {
                    learnStatus.setText("Test failed\n" + e.getMessage());
                    testLast.setEnabled(true);
                });
            }
        }, "apollo-test-command").start();
    }

    private JSONObject requestJson(
            String method,
            String url,
            String authToken,
            String body
    ) throws Exception {
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
                        code >= 400
                                ? connection.getErrorStream()
                                : connection.getInputStream(),
                        StandardCharsets.UTF_8
                )
        );

        StringBuilder text = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            text.append(line);
        }
        reader.close();
        connection.disconnect();

        if (code >= 400) {
            throw new IllegalStateException("Server returned HTTP " + code + ": " + text);
        }

        return new JSONObject(text.toString());
    }

    private String cleanBaseUrl(String value) {
        String cleaned = value.trim();
        while (cleaned.endsWith("/")) {
            cleaned = cleaned.substring(0, cleaned.length() - 1);
        }
        return cleaned;
    }

    private void refreshStatus() {
        ConsumerIrManager ir =
                (ConsumerIrManager) getSystemService(Context.CONSUMER_IR_SERVICE);
        boolean emitter = ir != null && ir.hasIrEmitter();

        StringBuilder sb = new StringBuilder();
        sb.append("AVA IR emitter: ").append(emitter ? "READY" : "NOT AVAILABLE").append("\n");
        sb.append("Bridge: port 8765 · raw IR ready");

        status.setText(sb.toString());
    }
}
