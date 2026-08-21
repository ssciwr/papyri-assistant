"""Errors raised when a client's decision cannot be applied to a paused run."""


class DecisionError(Exception):
    """Base for decision replies the agent refuses to hand to the graph."""


class StaleDecision(DecisionError):
    """The decision answers an interrupt that is no longer the pending one.

    Raised when nothing is paused at all, or when the reply names a different
    interrupt than the one the run is waiting on. The client's view of the
    conversation is out of date; it should drop the dialog rather than retry.
    """


class InvalidDecision(DecisionError):
    """The decision is malformed, or was never offered for its action.

    Raised when the reply carries the wrong number of decisions for the paused
    actions, or names a type outside that action's ``allowed_decisions``. Both
    would raise ``ValueError`` inside the graph, so they are caught before it
    runs.
    """
