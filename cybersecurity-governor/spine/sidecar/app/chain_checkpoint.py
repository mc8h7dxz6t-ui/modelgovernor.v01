"""Shim — canonical implementation in spine_core.chain_checkpoint (M1)."""
from spine_core.chain_checkpoint import (  # noqa: F401
    VerifyCheckpoint,
    count_events,
    load_checkpoint,
    save_checkpoint,
    schema_supports_checkpoints,
)
