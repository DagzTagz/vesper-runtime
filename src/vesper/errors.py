"""Exit-coded errors. CLI maps these to process status."""


class VesperError(Exception):
    """Base error. Subclasses set exit_code."""

    exit_code = 1


class UsageError(VesperError):
    """Bad arguments. Exit 1."""

    exit_code = 1


class ValidationError(VesperError):
    """Schema, path, or document validation failed. Exit 2."""

    exit_code = 2


class CryptoError(VesperError):
    """Signature or key material failed a check. Exit 2."""

    exit_code = 2


class IOPermissionError(VesperError):
    """Filesystem permissions or I/O refused. Exit 3."""

    exit_code = 3
