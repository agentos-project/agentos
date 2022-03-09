import arrow  # noqa: F401


# A basic agent.
class BasicAgent:
    DEFAULT_ENTRY_POINT = "evaluate"

    def evaluate(self):
        import bottle  # noqa: F401

        print("Successful venv test")
