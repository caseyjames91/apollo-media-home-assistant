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
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {
    private static final String PREFS = "apollo_ir_bridge";
    private static final String DEFAULT_HA_URL = "http://homeassistant.local:8100";

    private final Handler handler = new Handler(Looper.getMainLooper());

    private TextView status;
    private TextView learnStatus;
    private EditText haUrl;
    private EditText token;
    private EditText learner;
    private EditText deviceName;
    private EditText commandName;
    private Button learnIr;
    private Button learnRf;

    private SharedPreferences prefs;

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
        title.setText("Apollo AVA Bridge 0.6.0");
        title.setTextSize(24);
        root.addView(title);

        status = new TextView(this);
        status.setTextSize(14);
        status.setPadding(0, dp(8), 0, dp(12));
        root.addView(status);

        Button start = new Button(this);
        start.setText("Start IR Bridge");
        start.setOnClickListener(v -> startBridge());
        root.addView(start);

        addSection(root, "Home Assistant");

        haUrl = addField(root, "Apollo IR Server URL", false);
        token = addField(root, "Apollo IR API key (optional)", true);
        learner = addField(root, "BroadLink learner entity", false);

        haUrl.setText(prefs.getString("ha_url", DEFAULT_HA_URL));
        token.setText(prefs.getString("ha_token", ""));
        learner.setText(prefs.getString("learner", ""));

        Button save = new Button(this);
        save.setText("Save Apollo IR Settings");
        save.setOnClickListener(v -> saveSettings());
        root.addView(save);

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
        learnStatus.setTextSize(17);
        learnStatus.setPadding(0, dp(12), 0, dp(12));
        root.addView(learnStatus);

        TextView note = new TextView(this);
        note.setText(
                "Learning is performed by Apollo IR Server through Home Assistant and the selected BroadLink remote. "
                        + "The AVA is the user interface; Home Assistant remains hidden in the backend."
        );
        note.setPadding(0, dp(8), 0, dp(12));
        root.addView(note);

        setContentView(scroll);
        startBridge();
        refreshStatus();
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
        prefs.edit()
                .putString("ha_url", cleanBaseUrl(haUrl.getText().toString()))
                .putString("ha_token", token.getText().toString().trim())
                .putString("learner", learner.getText().toString().trim())
                .apply();
        learnStatus.setText("Apollo IR settings saved.");
    }

    private void setLearning(boolean busy) {
        learnIr.setEnabled(!busy);
        learnRf.setEnabled(!busy);
        deviceName.setEnabled(!busy);
        commandName.setEnabled(!busy);
    }

    private void startLearn(String type) {
        saveSettings();

        String base = prefs.getString("ha_url", "").trim();
        String auth = prefs.getString("ha_token", "").trim();
        String remote = prefs.getString("learner", "").trim();
        String device = deviceName.getText().toString().trim();
        String command = commandName.getText().toString().trim();

        if (base.isEmpty() || remote.isEmpty()) {
            learnStatus.setText("Set the Apollo IR Server URL and BroadLink learner first.");
            return;
        }
        if (device.isEmpty() || command.isEmpty()) {
            learnStatus.setText("Enter both a device name and command name.");
            return;
        }

        setLearning(true);
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
                        auth,
                        body.toString()
                );

                String id = response.getString("id");
                handler.post(() -> {
                    learnStatus.setText(
                            type.equals("rf")
                                    ? "Learning RF — follow the BroadLink learning sequence and hold/press the original remote button."
                                    : "Learning IR — point the original remote at the BroadLink and press the button."
                    );
                });
                pollJob(base, auth, id);
            } catch (Exception e) {
                handler.post(() -> {
                    learnStatus.setText("Could not start learning: " + e.getMessage());
                    setLearning(false);
                });
            }
        }, "apollo-ha-learn").start();
    }

    private void pollJob(String base, String auth, String id) {
        new Thread(() -> {
            try {
                while (true) {
                    Thread.sleep(900);
                    JSONObject job = requestJson(
                            "GET",
                            base + "/api/jobs/" + id,
                            auth,
                            null
                    );

                    String state = job.optString("state", "unknown");
                    String message = job.optString("message", state);

                    handler.post(() -> learnStatus.setText(message));

                    if (state.equals("learned")
                            || state.equals("timeout")
                            || state.equals("error")
                            || state.equals("cancelled")) {
                        handler.post(() -> setLearning(false));
                        return;
                    }
                }
            } catch (Exception e) {
                handler.post(() -> {
                    learnStatus.setText("Lost learning status: " + e.getMessage());
                    setLearning(false);
                });
            }
        }, "apollo-ha-job").start();
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
            throw new IllegalStateException("HA returned HTTP " + code + ": " + text);
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
        sb.append("Bridge: http://0.0.0.0:8765\n");
        sb.append("Raw IR: POST /ir/raw\n");

        status.setText(sb.toString());
    }
}
