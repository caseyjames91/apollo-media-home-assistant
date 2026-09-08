package com.apollo.avairbridge;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.hardware.ConsumerIrManager;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private TextView status;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int p = (int) (20 * getResources().getDisplayMetrics().density);
        root.setPadding(p, p, p, p);

        TextView title = new TextView(this);
        title.setText("AVA IR Bridge 0.3.0");
        title.setTextSize(24);
        root.addView(title);

        status = new TextView(this);
        status.setTextSize(15);
        status.setPadding(0, p / 2, 0, p / 2);
        root.addView(status);

        Button start = new Button(this);
        start.setText("Start IR Bridge");
        start.setOnClickListener(v -> startBridge());
        root.addView(start);

        TextView note = new TextView(this);
        note.setText("Generic bridge only. Home Assistant supplies learned BroadLink codes at transmit time; no device commands are stored in the APK.");
        note.setPadding(0, p / 2, 0, p / 2);
        root.addView(note);

        setContentView(root);
        startBridge();
        refreshStatus();
    }


    private void startBridge() {
        Intent i = new Intent(this, IrBridgeService.class);
        if (android.os.Build.VERSION.SDK_INT >= 26) startForegroundService(i); else startService(i);
        refreshStatus();
    }

    private void refreshStatus() {
        ConsumerIrManager ir = (ConsumerIrManager) getSystemService(Context.CONSUMER_IR_SERVICE);
        boolean emitter = ir != null && ir.hasIrEmitter();
        StringBuilder sb = new StringBuilder();
        sb.append("IR emitter: ").append(emitter ? "YES" : "NO").append("\n");
        sb.append("HTTP port: 8765\n");
        sb.append("Status: GET /status\n");
        sb.append("Generic learned code: POST /ir/broadlink\n");
        if (ir != null) {
            ConsumerIrManager.CarrierFrequencyRange[] ranges = ir.getCarrierFrequencies();
            if (ranges != null) {
                sb.append("Carrier ranges:\n");
                for (ConsumerIrManager.CarrierFrequencyRange r : ranges) {
                    sb.append("  ").append(r.getMinFrequency()).append("-").append(r.getMaxFrequency()).append(" Hz\n");
                }
            }
        }
        status.setText(sb.toString());
    }
}
