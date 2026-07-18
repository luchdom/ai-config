"""Typed failures for the canonical local-work base package."""


class DeliveryBaseError(RuntimeError):
    """Base class for deterministic, fail-closed workflow errors."""


class ValidationError(DeliveryBaseError):
    """Input or persisted data did not satisfy the canonical contract."""


class RepositoryIdentityError(DeliveryBaseError):
    """Git could not prove the requested repository/worktree identity."""


class StateHomeError(DeliveryBaseError):
    """The machine-stable repository state home is unsafe or incompatible."""


class MutexTimeoutError(DeliveryBaseError):
    """The allocation/registry mutex could not be acquired in time."""


class ConcurrentUpdateError(DeliveryBaseError):
    """An atomic compare-and-swap observed an unexpected revision."""


class CollisionError(DeliveryBaseError):
    """A key, path, or external tracking identity is already allocated."""


class UnsafePathError(DeliveryBaseError):
    """A path failed containment, alias, or reparse-point validation."""


class ResumeError(DeliveryBaseError):
    """An exact workflow selector could not be resumed safely."""


class HandoffError(DeliveryBaseError):
    """A workflow-managed Handoff could not be completed atomically."""
