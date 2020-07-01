import random
import tensorflow as tf
import tensorflow.keras as keras
import numpy as np
import pandas as pd
import gym

num_episodes = 1000
max_steps_per_episode = 200
batch_size = 32

num_actions = 2

discount_rate = 0.95

model = keras.Sequential([keras.layers.Dense(16, input_shape=(4,), activation="elu"),
                          keras.layers.Dense(16, activation="elu"),
                          keras.layers.Dense(num_actions)])
optimizer = keras.optimizers.Adam(lr=0.01)

memory_buffer = pd.DataFrame(columns=["states", "actions", "rewards", "next_states", "dones"])
best_score, best_model = 0, None
all_scores = []
env = gym.make('CartPole-v1')
for episode_num in range(num_episodes):
    state = env.reset()
    done = False
    step_num = 0
    while step_num < max_steps_per_episode:
        step_num += 1
        q_vals = model(state[np.newaxis])
        epsilon = min(0.9, 40.0 / (episode_num + 1))  # decay epsilon so that we can converge to Q*
        if episode_num % 20 == 0 and step_num == 1:
            print("epsilon is %s" % epsilon)
        if np.random.random() < epsilon:  # with epsilon probability, act randomly.
            action = env.action_space.sample()
        else:
            action = np.argmax(q_vals)  # with 1-epsilon probability, use the policy
        next_state, reward, done, _ = env.step(action)
        memory_buffer.loc[len(memory_buffer)] = [state, action, reward, next_state, done]
        state = next_state
        if done:
            break
    if step_num > best_score:  # keep our best model so that we can
        print(f"saving best model to disk with score {step_num}")
        best_model = model.save("best_model")
        best_score = step_num
    all_scores.append(step_num)
    if step_num == 200:
        print("reached score target of 200!")
        break

    if episode_num > 50:  # let memory build up a bit before starting to iterate on the model
        indices = [x for x in range(len(memory_buffer))]
        random.shuffle(indices)
        batch_indices = indices[:batch_size]
        observations = memory_buffer.iloc[batch_indices]
        next_per_action_q_vals = model(np.vstack(observations.next_states))
        next_q_vals = np.max(next_per_action_q_vals, axis=1)
        target_q_vals = observations.rewards + (1 - observations.dones) * discount_rate * next_q_vals


        def loss():
            per_action_q_vals = model(np.vstack(observations.states))
            action_selector = tf.one_hot(tf.math.argmax(per_action_q_vals, axis=1), depth=2, on_value=1.0,
                                         off_value=0.0)
            q_vals = tf.reduce_sum(action_selector * per_action_q_vals, axis=1)
            return tf.reduce_mean(tf.square(q_vals - target_q_vals))


        optimizer.minimize(loss, model.trainable_variables)

#if __name__ == "__main__":
