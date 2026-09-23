package ai.tessaris.pilot

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.Signature
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Keeps Pilot's Ed25519 protocol key wrapped by a non-exportable Android Keystore AES key.
 * The wrapping key requires recent strong-biometric or device-credential authentication.
 */
class PilotPossessionVault {
    private val alias = "pilot-possession-wrap-v1"
    private val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

    fun ensureWrappingKey(): SecretKey {
        (store.getKey(alias, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setUserAuthenticationRequired(true)
            .setUserAuthenticationParameters(30, KeyProperties.AUTH_BIOMETRIC_STRONG or KeyProperties.AUTH_DEVICE_CREDENTIAL)
            .setInvalidatedByBiometricEnrollment(true)
            .build())
        return generator.generateKey()
    }

    fun createProtocolKey(): ProtocolKey {
        val pair = KeyPairGenerator.getInstance("Ed25519").generateKeyPair()
        val rawPublic = pair.public.encoded.takeLast(32).toByteArray()
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, ensureWrappingKey())
        return ProtocolKey(rawPublic, cipher.iv, cipher.doFinal(pair.private.encoded))
    }

    fun signingCipher(iv: ByteArray): Cipher = Cipher.getInstance("AES/GCM/NoPadding").apply {
        init(Cipher.DECRYPT_MODE, ensureWrappingKey(), GCMParameterSpec(128, iv))
    }

    fun signAfterBiometric(cipher: Cipher, wrappedPrivate: ByteArray, canonicalPayload: ByteArray): ByteArray {
        val privateBytes = cipher.doFinal(wrappedPrivate)
        val factory = java.security.KeyFactory.getInstance("Ed25519")
        val privateKey = factory.generatePrivate(java.security.spec.PKCS8EncodedKeySpec(privateBytes))
        return Signature.getInstance("Ed25519").run { initSign(privateKey); update(canonicalPayload); sign() }
    }

    data class ProtocolKey(val rawPublicKey: ByteArray, val iv: ByteArray, val wrappedPrivateKey: ByteArray)
}
