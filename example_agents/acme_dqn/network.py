import sonnet as snt


class AcmeDQNNetwork:
    def __init__(self, **kwargs):
        self.net = snt.Sequential(
            [
                snt.Flatten(),
                snt.nets.MLP(
                    [50, 50, self.environment.get_spec().actions.num_values]
                ),
            ]
        )
        self.restore()

    def restore(self):
        self.tracker.restore_tensorflow("network", self.net)

    def save(self):
        self.tracker.save_tensorflow("network", self.net)
