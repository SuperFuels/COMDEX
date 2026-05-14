"""
Tessaris * UltraQC v0.4-SLE
Feature flag configuration module.
Used to toggle core systems at runtime (for development and testing).
"""

import os

# Global feature flags - can be overridden by environment variables
LIGHTWAVE_ENGINE_ON = os.getenv("LIGHTWAVE_ENGINE_ON", "true").lower() == "true"
QQC_ON = os.getenv("QQC_ON", "true").lower() == "true"

def is_lightwave_enabled():
    return LIGHTWAVE_ENGINE_ON

def is_qqc_enabled():
    return QQC_ON

def print_feature_status():
    print(f"[FeatureFlags] LIGHTWAVE_ENGINE_ON = {LIGHTWAVE_ENGINE_ON}")
    print(f"[FeatureFlags] QQC_ON = {QQC_ON}")