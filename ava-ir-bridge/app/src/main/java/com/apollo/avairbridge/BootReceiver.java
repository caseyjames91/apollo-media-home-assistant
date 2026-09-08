package com.apollo.avairbridge;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) {
            Intent svc = new Intent(context, IrBridgeService.class);
            if (android.os.Build.VERSION.SDK_INT >= 26) context.startForegroundService(svc); else context.startService(svc);
        }
    }
}
