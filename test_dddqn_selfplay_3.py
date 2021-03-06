from environments.snake_env import SnakeEnvironment
import os
from dddqn_model.dddqn import *
import time

saving_path = "models_selfplay_3"
load_model_path = "models_selfplay_3"

batch_size = 512  # How many experiences to use for each training step.
update_freq = 4  # How often to perform a training step.
y = .99  # Discount factor on the target Q-values
startE = 0.1  # Starting chance of random action
endE = 0.0001  # Final chance of random action
annealing_steps = 500000.  # How many steps of training to reduce startE to endE.
num_episodes = 200  # How many episodes of game environment to train network with.
pre_train_steps = 5000  # How many steps of random actions before training begins.
max_epLength = 5000000  # The max allowed length of our episode.
load_model = True  # Whether to load a saved PPO_implementation.
h_size = 1296 * 2  # The size of the final convolutional layer before splitting it into Advantage and Value streams.
tau = 0.001  # Rate to update target network toward primary network


def main():

    # Environment setting
    spacing = 22
    dimensions = 15
    history = 4
    env = SnakeEnvironment(num_agents=3, num_fruits=3, spacing=spacing, dimensions=dimensions, flatten_states=False,
                           reward_killed=-1.0, history=history)
    env.reset()

    # Tensorflow PPO_implementation setting
    tf.compat.v1.disable_eager_execution()
    tf.compat.v1.reset_default_graph()

    # Create Main Agent
    agent_1 = Qnetwork(h_size=h_size, scope="main_agent_1")
    agent_1_targetQN = Qnetwork(h_size=h_size, scope="target_agent_1")

    # Create Adversary agents
    agent_2 = Qnetwork(h_size=h_size, scope="main_agent_2")

    agent_3 = Qnetwork(h_size=h_size, scope="main_agent_3")

    # Tensorflow restore weight setting
    init = tf.compat.v1.global_variables_initializer()

    # Trainable variable for pretrain agent, agent1, agent2
    trainables = tf.compat.v1.trainable_variables()

    weights_agent_1 = [v for v in trainables if v.name.split('/')[0] in ['main_agent_1', 'target_agent_1']]

    weights_agent_2 = [v for v in trainables if v.name.split('/')[0] in ['main_agent_2']]

    weights_agent_3 = [v for v in trainables if v.name.split('/')[0] in ['main_agent_3']]

    # Copy weight of agent1 to agent2

    update_weights = [tf.compat.v1.assign(weights_2, weights_1) for (weights_2, weights_1) in
                      zip(weights_agent_2, weights_agent_1)]

    update_weights_agent_3 = [tf.compat.v1.assign(weights_3, weights_1) for (weights_3, weights_1) in
                              zip(weights_agent_3, weights_agent_1)]

    # Tensorflow Saver for agent2
    saver_new_model = tf.compat.v1.train.Saver(weights_agent_1)

    # Create lists to contain total rewards and steps per episode
    reward_list_agent_3 = []
    reward_list_agent_2 = []
    reward_list_agent_1 = []

    # Make a path for our PPO_implementation to be saved in.
    if not os.path.exists(saving_path):
        os.makedirs(saving_path)

    config = tf.compat.v1.ConfigProto()
    config.gpu_options.allow_growth = True
    with tf.compat.v1.Session() as sess:
        sess.run(init)
        sess.run(update_weights)
        sess.run(update_weights_agent_3)

        if load_model == True:
            ckpt = tf.train.get_checkpoint_state(load_model_path)
            saver_new_model.restore(sess, ckpt.model_checkpoint_path)
            sess.run(update_weights)
            sess.run(update_weights_agent_3)
            print('Loading Saving Model...@:')
            print(ckpt.model_checkpoint_path)


        for i in range(num_episodes):

            for k in range(0, 100):

                # Reset environment and get first new observation
                obs = env.reset()

                # Initialize state, reward, end flag of agent1, agent2
                obs_agent_1 = obs[0]
                obs_agent_2 = obs[1]
                obs_agent_3 = obs[2]

                # Initialize sum of reward of agent1, agent2
                sum_rewards_agent_3 = 0
                sum_rewards_agent_2 = 0
                sum_rewards_agent_1 = 0

                # The Q-Network
                for j in range(0, max_epLength):
                    env.render()
                    time.sleep(0.1)

                    # Select action of agent3
                    action_agent_3 = sess.run(agent_3.predict, feed_dict={agent_3.imageIn: [obs_agent_3 / 3.0]})[
                            0]

                    # Select action of agent2
                    action_agent_2 = sess.run(agent_2.predict, feed_dict={agent_2.imageIn: [obs_agent_2 / 3.0]})[
                        0]

                    # Select action of agent1
                    action_agent_1 = sess.run(agent_1.predict, feed_dict={agent_1.imageIn: [obs_agent_1 / 3.0]})[
                        0]

                    next_obs, reward, done, d_common = env.step([action_agent_1, action_agent_2, action_agent_3])

                    reward_agent_1 = reward[0]
                    reward_agent_2 = reward[1]
                    reward_agent_3 = reward[2]

                    d_agent_1 = done[0]
                    d_agent_2 = done[1]
                    d_agent_3 = done[2]

                    next_obs_agent_1 = next_obs[0]
                    next_obs_agent_2 = next_obs[1]
                    next_obs_agent_3 = next_obs[2]

                    # Add a reward of each agent to total reward
                    sum_rewards_agent_3 += reward_agent_3
                    sum_rewards_agent_2 += reward_agent_2
                    sum_rewards_agent_1 += reward_agent_1

                    # Save a next state to current state for next step
                    obs_agent_3 = next_obs_agent_3
                    obs_agent_2 = next_obs_agent_2
                    obs_agent_1 = next_obs_agent_1

                    # agent 1 wins
                    if (d_agent_2 == True and d_agent_3 == True):
                        break
                    # agent 2 wins
                    elif (d_agent_1 == True and d_agent_3 == True):
                        break
                    # agent 3 wins
                    elif (d_agent_1 == True and d_agent_2 == True):
                        break


                # Save sum of each agent for printing performance
                reward_list_agent_3.append(sum_rewards_agent_3)
                reward_list_agent_2.append(sum_rewards_agent_2)
                reward_list_agent_1.append(sum_rewards_agent_1)


            # Periodically print performance of agents "step, most current mean reward, current explore rate"
            if len(reward_list_agent_2) % 10 == 0:
                print(i, "agent_3", np.mean(reward_list_agent_3[-10:]))
                print(i, "agent_2", np.mean(reward_list_agent_2[-10:]))
                print(i, "agent_1", np.mean(reward_list_agent_1[-10:]))
                print("")


if __name__ == '__main__':
    main()