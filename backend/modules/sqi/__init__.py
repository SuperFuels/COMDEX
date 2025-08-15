# -*- coding: utf-8 -*-
# Keep SQI package import lightweight to avoid circular import chains.

__all__ = ["push_drift_report_to_kg"]

def push_drift_report_to_kg(*args, **kwargs):
    """
    Lazy proxy for backend.modules.sqi.kg_drift.push_drift_report_to_kg
    to avoid circular imports during module init.
    """
    from .kg_drift import push_drift_report_to_kg as _real
    return _real(*args, **kwargs)