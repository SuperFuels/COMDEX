package ai.tessaris.pilot

import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.fragment.app.FragmentActivity

class PilotBiometricApproval(private val activity: FragmentActivity) {
    fun confirm(
        cipher: javax.crypto.Cipher,
        reason: String,
        onApproved: (javax.crypto.Cipher) -> Unit,
        onDenied: (String) -> Unit,
    ) {
        val prompt = BiometricPrompt(activity, activity.mainExecutor, object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                result.cryptoObject?.cipher?.let(onApproved) ?: onDenied("Missing protected signing operation")
            }
            override fun onAuthenticationError(code: Int, message: CharSequence) = onDenied(message.toString())
        })
        val info = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Approve with this trusted phone")
            .setSubtitle(reason)
            .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG or BiometricManager.Authenticators.DEVICE_CREDENTIAL)
            .build()
        prompt.authenticate(info, BiometricPrompt.CryptoObject(cipher))
    }
}
