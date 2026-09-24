"""
the two failures a cli_<command>.py function can raise. Imports nothing.

Each carries the message alone; main() catches it and does the reporting.
Nothing below the CLI layer raises either. A validator there returns a
(value, error) tuple instead, having no view of which command called it.
"""


class UsageError(Exception):
    """
    a value on the command line is not usable.

    main() prints the message with the usage line of the command that raised it.
    """


class ReadinessError(Exception):
    """
    the run cannot report success.

    Either something it needed was not there, or what it checked did not hold,
    the way verify finds changed content. main() prints the message alone, and nothing at all when the message is
    empty, for a command that has already said everything on stdout.
    """
