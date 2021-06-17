{file_header}
import agentos


# A basic agent.
class {agent_name}(agentos.Agent):
    def learn(self):
        if self.verbose:
            print("{agent_name} is performing a rollout to improve its policy")
        self.rollout(should_learn=True)

    def advance(self):
        if self.verbose:
            print("{agent_name} is taking an action")
        prev_obs, action, obs, reward, done, info = self.step()
        if self.verbose:
            print("\tPrevious Observation: " + str(prev_obs))
            print("\tAction:               " + str(action))
            print("\tObservation:          " + str(obs))
            print("\tReward:               " + str(reward))
            print("\tDone:                 " + str(done))
            print("\tInfo:                 " + str(info))
            print()
        return done
