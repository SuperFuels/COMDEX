package ai.tessaris.pilot

import android.app.NotificationChannel
import android.app.NotificationManager
import androidx.core.app.NotificationCompat
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import android.content.Context
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class PilotMessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(message: RemoteMessage) {
        // Push data contains only an opaque event id. Private content is fetched from the paired mother.
        val eventID = message.data["event_id"] ?: return
        val request = OneTimeWorkRequestBuilder<PilotInboxRefreshWorker>()
            .addTag("pilot-inbox-$eventID")
            .build()
        WorkManager.getInstance(this).enqueueUniqueWork(
            "pilot-inbox-$eventID", androidx.work.ExistingWorkPolicy.KEEP, request
        )
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel("pilot-private", "Pilot updates", NotificationManager.IMPORTANCE_DEFAULT))
        manager.notify(eventID.hashCode(), NotificationCompat.Builder(this, "pilot-private")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("Pilot")
            .setContentText("Open Pilot to view a private update.")
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .build())
    }
}

class PilotInboxRefreshWorker(context: Context, parameters: WorkerParameters) : Worker(context, parameters) {
    override fun doWork(): Result {
        // The production connection store performs a signed, cursor-based Inbox refresh here.
        return Result.success()
    }
}
