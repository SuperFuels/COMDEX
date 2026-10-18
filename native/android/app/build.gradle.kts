plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "ai.tessaris.pilot"
    compileSdk = 35
    defaultConfig {
        applicationId = "ai.tessaris.pilot"
        minSdk = 28
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }
    buildFeatures { compose = true }
    composeOptions { kotlinCompilerExtensionVersion = "1.5.15" }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation("androidx.fragment:fragment-ktx:1.8.5")
    implementation("androidx.biometric:biometric:1.2.0-alpha05")
    implementation("androidx.compose.material3:material3:1.3.1")
    implementation("androidx.work:work-runtime-ktx:2.10.0")
    implementation("com.google.firebase:firebase-messaging:24.1.0")
}
