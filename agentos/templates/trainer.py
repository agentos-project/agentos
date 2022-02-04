{file_header}


class BasicTrainer:
    def train(self):
        transition_count = sum([len(e) for e in self.dataset.episodes])
        print("\nTrainer: dataset has", transition_count, "transitions")
        print("\tTrainer: No-op training policy", str(self.policy))
