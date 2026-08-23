"""The pipeline stages, one module per CLI command.

Each ``run()`` takes the loaded ``Config`` and an open database connection,
does its work, and returns a dict of counts for the CLI to print. Worker
threads never touch the connection: they return results to the main thread,
which performs every database write.
"""
