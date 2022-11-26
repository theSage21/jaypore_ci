class Pipeline:
    def __init__(self, image="python:3.11", timeout="15m"):
        self.image = image
        self.timeout = timeout
        self.__history__ = []

    def job(self, *commands, *, image=None, timeout=None):
        return self

    def ok(self):
        return self.last_command.exit_code == 0
