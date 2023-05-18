from jaypore_ci import jci


def __get_pipe_id__(self):
    return f"fake_docker_container_id_{self.repo.sha}"


jci.Pipeline.__get_pipe_id__ = __get_pipe_id__
