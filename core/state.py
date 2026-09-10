"""Shared mutable application state.

IMPORTANT: other modules must import this module and access the
attributes as `state.HAS_SUDO_PERM` / `state.IS_DRY_RUN`, NOT do
`from core.state import HAS_SUDO_PERM` (which copies the value once
and breaks synchronization) or use a bare `global` (which only ever
affects the copy inside that one file).

This is the reason CleanX (and any split of it) needs this file: the
original single-file version used plain `global HAS_SUDO_PERM` /
`global IS_DRY_RUN` which only works because everything lived in one
module. Splitting into multiple files requires a single shared owner
for this state, which is exactly what this module is.
"""

HAS_SUDO_PERM: bool = False
IS_DRY_RUN: bool = False
