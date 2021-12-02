RUN_CREATE_DATA = {
    "root_name": "agent",
    "agent_name": "agent",
    "component_spec": {
        "components": {
            "agent==f39000a113abf6d7fcd93f2eaabce4cab8873fb0": {
                "class_name": "SB3PPOAgent",
                "dependencies": {
                    "environment": (
                        "environment=="
                        "f39000a113abf6d7fcd93f2eaabce4cab8873fb0"
                    ),
                    "tracker": (
                        "tracker==f39000a113abf6d7fcd93f2eaabce4cab8873fb0"
                    ),
                },
                "file_path": "example_agents/sb3_agent/agent.py",
                "repo": "sb3_agent_dir",
            },
            "environment==f39000a113abf6d7fcd93f2eaabce4cab8873fb0": {
                "class_name": "CartPole",
                "dependencies": {},
                "file_path": "example_agents/sb3_agent/environment.py",
                "repo": "sb3_agent_dir",
            },
            "tracker==f39000a113abf6d7fcd93f2eaabce4cab8873fb0": {
                "class_name": "SB3Tracker",
                "dependencies": {},
                "file_path": "example_agents/sb3_agent/tracker.py",
                "repo": "sb3_agent_dir",
            },
        },
        "repos": {
            "sb3_agent_dir": {
                "type": "github",
                "url": "https://github.com/nickjalbert/agentos.git",
            }
        },
    },
    "entry_point": "evaluate",
    "environment_name": "environment",
    "metrics": {
        "episode_count": 10.0,
        "max_reward": 501.0,
        "mean_reward": 501.0,
        "median_reward": 501.0,
        "min_reward": 501.0,
        "step_count": 5010.0,
        "training_episode_count": 356.0,
        "training_step_count": 53248.0,
    },
    "parameter_set": {"agent": {"evaluate": {"n_eval_episodes": "10"}}},
}
