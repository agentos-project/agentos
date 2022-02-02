{file_header}


class BasicTrainer:
    def train(self):
        transition_count = len(self.dataset.transitions)
        print("\nTrainer: dataset has", transition_count, "transitions")
        print("\tTrainer: No-op training policy", str(self.policy))
