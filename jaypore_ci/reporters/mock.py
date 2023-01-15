from jaypore_ci.interfaces import Reporter


class Mock(Reporter):
    def render(self, pipeline):
        return f"{pipeline}"
