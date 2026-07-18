"""Canonical SAAS-45 local-work primitives for all delivery workflows."""

from .descriptor import WORK_DESCRIPTOR_VERSION, inspect_historical_artifact, validate_descriptor
from .identity import IDENTITY_VERSION, RepositoryIdentity, observe_repository_identity
from .registry import REGISTRY_VERSION, WorkflowRegistry
from .state_home import STATE_HOME_VERSION, derive_state_home, ensure_state_home
from .workflow_init import BASE_PACKAGE_VERSION, ProviderObservedWork, WorkflowManager

__all__ = [
    "BASE_PACKAGE_VERSION",
    "IDENTITY_VERSION",
    "REGISTRY_VERSION",
    "STATE_HOME_VERSION",
    "WORK_DESCRIPTOR_VERSION",
    "ProviderObservedWork",
    "RepositoryIdentity",
    "WorkflowManager",
    "WorkflowRegistry",
    "derive_state_home",
    "ensure_state_home",
    "inspect_historical_artifact",
    "observe_repository_identity",
    "validate_descriptor",
]
