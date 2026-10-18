"""Workflow capsule connector adapters.

MVP rule:
- connector reads may be simulated or adapter-backed
- connector drafts are draft-only
- connector external writes are never executed from dry-run
"""
