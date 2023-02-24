import random
from collections import defaultdict

import pendulum
import docker


def cid(short=False):
    n_chars = 12 if short else 64
    return "".join(random.sample("0123456789abcdef" * 10, n_chars))


class Network:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def remove(self):
        pass


class Networks:
    nets = {}

    def list(self, names):
        return list(filter(None, [self.nets.get(name) for name in names]))

    def create(self, **kwargs):
        name = kwargs.get("name")
        self.nets[name] = Network(**kwargs)
        return name

    def get(self, name):
        return self.nets[name]


class Container:
    def __init__(self, **kwargs):
        self.id = cid()
        self.__dict__.update(kwargs)
        self.FinishedAt = "0001-01-01T00:00:00Z"
        self.ExitCode = 0

    def logs(self):
        return b""

    def stop(self, **_):
        self.FinishedAt = str(pendulum.now())
        self.ExitCode = 0


class Containers:
    boxes = {}

    def get(self, container_id):
        return self.boxes[container_id]

    def run(self, **kwargs):
        kwargs["StartedAt"] = str(pendulum.now())
        c = Container(**kwargs)
        self.boxes[c.id] = c
        return c


class Docker:
    networks = Networks()
    containers = Containers()


class APIClient:
    max_running = {}
    reported_running = defaultdict(int)

    def inspect_container(self, container_id):
        if container_id not in self.max_running:
            self.max_running[container_id] = random.choice(range(3, 11))
        self.reported_running[container_id] += 1
        is_running = (
            self.reported_running[container_id] <= self.max_running[container_id]
        )
        container = Containers.boxes[container_id]
        return {
            "State": {
                "Running": is_running,
                "ExitCode": container.ExitCode,
                "StartedAt": container.StartedAt,
                "FinishedAt": container.FinishedAt,
            }
        }


def from_env():
    return Docker()


docker.from_env = from_env
docker.APIClient = APIClient
