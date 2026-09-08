package com.apollo.avairbridge;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.hardware.ConsumerIrManager;
import android.os.Build;
import android.os.IBinder;
import android.util.Base64;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

public class IrBridgeService extends Service {
    private static final int PORT = 8765;
    private static final int DEFAULT_CARRIER_HZ = 38000;
    private static final String CHANNEL_ID = "ava_ir_bridge";
    private static final int MAX_PATTERN_US = 2_000_000;
    private static final int MAX_PATTERN_ITEMS = 10000;

    private volatile boolean running;
    private ServerSocket server;

    @Override
    public void onCreate() {
        super.onCreate();
        createChannel();

        Intent open = new Intent(this, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(
                this,
                0,
                open,
                Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0
        );

        android.app.Notification.Builder b = Build.VERSION.SDK_INT >= 26
                ? new android.app.Notification.Builder(this, CHANNEL_ID)
                : new android.app.Notification.Builder(this);

        b.setContentTitle("AVA IR Bridge")
                .setContentText("Listening on port " + PORT)
                .setSmallIcon(android.R.drawable.stat_sys_data_bluetooth)
                .setContentIntent(pi)
                .setOngoing(true);

        startForeground(8765, b.build());
        startServer();
    }

    private void createChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(
                    CHANNEL_ID,
                    "AVA IR Bridge",
                    NotificationManager.IMPORTANCE_LOW
            );
            getSystemService(NotificationManager.class).createNotificationChannel(ch);
        }
    }

    private void startServer() {
        if (running) return;
        running = true;

        new Thread(() -> {
            try {
                server = new ServerSocket(PORT);
                while (running) {
                    Socket s = server.accept();
                    handle(s);
                }
            } catch (Exception ignored) {
            }
        }, "ava-ir-http").start();
    }

    private void handle(Socket socket) {
        try (Socket s = socket;
             BufferedReader r = new BufferedReader(
                     new InputStreamReader(s.getInputStream(), StandardCharsets.US_ASCII)
             );
             OutputStream out = s.getOutputStream()) {

            String first = r.readLine();
            if (first == null) return;

            String[] parts = first.split(" ");
            String method = parts.length > 0 ? parts[0] : "";
            String rawPath = parts.length > 1 ? parts[1] : "";
            String path = rawPath.split("\\?", 2)[0];

            int contentLength = 0;
            String line;

            while ((line = r.readLine()) != null && !line.isEmpty()) {
                int colon = line.indexOf(':');
                if (colon > 0
                        && "content-length".equalsIgnoreCase(line.substring(0, colon).trim())) {
                    try {
                        contentLength = Integer.parseInt(line.substring(colon + 1).trim());
                    } catch (NumberFormatException ignored) {
                    }
                }
            }

            char[] bodyChars = new char[Math.max(0, contentLength)];
            int read = 0;

            while (read < bodyChars.length) {
                int n = r.read(bodyChars, read, bodyChars.length - read);
                if (n < 0) break;
                read += n;
            }

            String requestBody = new String(bodyChars, 0, read).trim();

            String body;
            int code = 200;

            if ("GET".equals(method) && "/status".equals(path)) {
                ConsumerIrManager ir =
                        (ConsumerIrManager) getSystemService(Context.CONSUMER_IR_SERVICE);

                body = "{\"ok\":true,\"emitter\":"
                        + (ir != null && ir.hasIrEmitter())
                        + ",\"port\":" + PORT
                        + ",\"formats\":[\"raw\",\"broadlink_base64\"]}";
            } else if ("POST".equals(method) && "/ir/raw".equals(path)) {
                try {
                    RawRequest raw = parseRawRequest(requestBody);
                    transmitRaw(this, raw.carrierHz, raw.pattern);
                    body = "{\"ok\":true,\"format\":\"raw\","
                            + "\"carrier_hz\":" + raw.carrierHz + ","
                            + "\"pulses\":" + raw.pattern.length + "}";
                } catch (Exception e) {
                    code = 400;
                    body = errorJson(e);
                }
            } else if ("POST".equals(method) && "/ir/broadlink".equals(path)) {
                try {
                    if (requestBody.isEmpty()) {
                        throw new IllegalArgumentException(
                                "Request body must be a BroadLink Base64 IR code"
                        );
                    }
                    int carrier = queryInt(rawPath, "carrier", DEFAULT_CARRIER_HZ);
                    int[] pattern = transmitBroadlink(this, requestBody, carrier);
                    body = "{\"ok\":true,\"format\":\"broadlink_base64\","
                            + "\"carrier_hz\":" + carrier + ","
                            + "\"pulses\":" + pattern.length + "}";
                } catch (Exception e) {
                    code = 400;
                    body = errorJson(e);
                }
            } else {
                code = 404;
                body = "{\"ok\":false,\"error\":\"not_found\"}";
            }

            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
            String reason = code == 200
                    ? "OK"
                    : code == 404
                    ? "Not Found"
                    : code == 400
                    ? "Bad Request"
                    : "Error";

            String hdr = "HTTP/1.1 " + code + " " + reason + "\r\n"
                    + "Content-Type: application/json\r\n"
                    + "Content-Length: " + bytes.length + "\r\n"
                    + "Connection: close\r\n\r\n";

            out.write(hdr.getBytes(StandardCharsets.US_ASCII));
            out.write(bytes);
            out.flush();
        } catch (Exception ignored) {
        }
    }

    private static RawRequest parseRawRequest(String body) throws Exception {
        if (body == null || body.trim().isEmpty()) {
            throw new IllegalArgumentException("Request body must be JSON");
        }

        JSONObject json = new JSONObject(body);
        int carrier = json.optInt("modulation_hz", DEFAULT_CARRIER_HZ);

        if (carrier < 10000 || carrier > 100000) {
            throw new IllegalArgumentException("modulation_hz must be between 10000 and 100000");
        }

        JSONArray timings = json.getJSONArray("timings_us");

        if (timings.length() < 2 || timings.length() > MAX_PATTERN_ITEMS) {
            throw new IllegalArgumentException(
                    "timings_us must contain between 2 and " + MAX_PATTERN_ITEMS + " items"
            );
        }

        int[] pattern = new int[timings.length()];
        long total = 0;

        for (int i = 0; i < timings.length(); i++) {
            long raw = timings.getLong(i);
            long abs = Math.abs(raw);

            if (abs < 1 || abs > Integer.MAX_VALUE) {
                throw new IllegalArgumentException("Every timing must be a non-zero integer");
            }

            total += abs;
            if (total >= MAX_PATTERN_US) {
                throw new IllegalArgumentException(
                        "IR pattern must be shorter than 2 seconds"
                );
            }

            pattern[i] = (int) abs;
        }

        return new RawRequest(carrier, pattern);
    }

    public static void transmitRaw(Context context, int carrierHz, int[] pattern) {
        ConsumerIrManager ir = requireIr(context);

        if (pattern == null || pattern.length < 2) {
            throw new IllegalArgumentException("IR pattern must contain at least two timings");
        }

        ir.transmit(carrierHz, pattern);
    }

    public static int[] transmitBroadlink(
            Context context,
            String base64Code,
            int carrierHz
    ) {
        int[] pattern = decodeBroadlinkIr(base64Code);

        if (pattern.length < 2) {
            throw new IllegalArgumentException(
                    "BroadLink code contained no usable IR pulse data"
            );
        }

        transmitRaw(context, carrierHz, pattern);
        return pattern;
    }

    private static ConsumerIrManager requireIr(Context context) {
        ConsumerIrManager ir =
                (ConsumerIrManager) context.getSystemService(Context.CONSUMER_IR_SERVICE);

        if (ir == null || !ir.hasIrEmitter()) {
            throw new IllegalStateException("No consumer IR emitter");
        }

        return ir;
    }

    public static int[] decodeBroadlinkIr(String base64Code) {
        byte[] packet;

        try {
            packet = Base64.decode(base64Code.trim(), Base64.DEFAULT);
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Invalid Base64 BroadLink code", e);
        }

        if (packet.length < 6) {
            throw new IllegalArgumentException("BroadLink packet too short");
        }

        if ((packet[0] & 0xff) != 0x26) {
            throw new IllegalArgumentException(
                    "Not a BroadLink IR packet (type 0x26)"
            );
        }

        int dataLength = (packet[2] & 0xff) | ((packet[3] & 0xff) << 8);
        int end = Math.min(packet.length, 4 + dataLength);
        int[] tmp = new int[Math.max(0, dataLength)];
        int count = 0;
        int i = 4;

        while (i < end) {
            int ticks = packet[i++] & 0xff;

            if (ticks == 0) {
                if (i + 1 >= end) break;
                ticks = ((packet[i] & 0xff) << 8) | (packet[i + 1] & 0xff);
                i += 2;
            }

            if (ticks == 0) continue;

            int micros = (int) Math.round(ticks * (8192.0 / 269.0));

            if (micros > 65535) break;

            tmp[count++] = Math.max(1, micros);
        }

        int[] result = new int[count];
        System.arraycopy(tmp, 0, result, 0, count);
        return result;
    }

    private static int queryInt(String rawPath, String key, int fallback) {
        int q = rawPath.indexOf('?');
        if (q < 0 || q + 1 >= rawPath.length()) return fallback;

        String[] pairs = rawPath.substring(q + 1).split("&");

        for (String pair : pairs) {
            String[] kv = pair.split("=", 2);

            if (kv.length == 2 && key.equals(kv[0])) {
                try {
                    return Integer.parseInt(kv[1]);
                } catch (NumberFormatException ignored) {
                    return fallback;
                }
            }
        }

        return fallback;
    }

    private static String errorJson(Exception e) {
        return "{\"ok\":false,\"error\":\""
                + jsonEscape(e.toString())
                + "\"}";
    }

    private static String jsonEscape(String s) {
        return s.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n");
    }

    private static final class RawRequest {
        final int carrierHz;
        final int[] pattern;

        RawRequest(int carrierHz, int[] pattern) {
            this.carrierHz = carrierHz;
            this.pattern = pattern;
        }
    }

    @Override
    public void onDestroy() {
        running = false;
        try {
            if (server != null) server.close();
        } catch (Exception ignored) {
        }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
