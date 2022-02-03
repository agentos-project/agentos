RUN_CREATE_DATA = {
    "artifacts": [],
    "component_spec": {
        "components": {
            "agent==73fbfe92028aec1a259935b5d809f1a7ee1e4336": {
                "class_name": "SB3PPOAgent",
                "dependencies": {
                    "environment": (
                        "environment==73fbfe92028aec1a259935b5d809f1a7ee1e4336"
                    ),
                    "run_manager": (
                        "run_manager==73fbfe92028aec1a259935b5d809f1a7ee1e4336"
                    ),
                },
                "file_path": "example_agents/sb3_agent/agent.py",
                "repo": "sb3_agent_dir",
                "instantiate": True,
            },
            "environment==73fbfe92028aec1a259935b5d809f1a7ee1e4336": {
                "class_name": "CartPole",
                "dependencies": {},
                "file_path": "example_agents/sb3_agent/environment.py",
                "repo": "sb3_agent_dir",
                "instantiate": True,
            },
            "run_manager==73fbfe92028aec1a259935b5d809f1a7ee1e4336": {
                "class_name": "SB3RunManager",
                "dependencies": {},
                "file_path": "example_agents/sb3_agent/run_manager.py",
                "repo": "sb3_agent_dir",
                "instantiate": True,
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
    "id": "39be22d7ff9848bd9545988ff15f578f",
    "is_publishable": True,
    "metrics": {
        "episode_count": 10.0,
        "max_reward": 10.0,
        "mean_reward": 9.1,
        "median_reward": 9.0,
        "min_reward": 8.0,
        "step_count": 91.0,
        "training_episode_count": 0.0,
        "training_step_count": 0.0,
    },
    "mlflow_data": {
        "metrics": {
            "episode_count": 10.0,
            "max_reward": 10.0,
            "mean_reward": 9.1,
            "median_reward": 9.0,
            "min_reward": 8.0,
            "step_count": 91.0,
            "training_episode_count": 0.0,
            "training_step_count": 0.0,
        },
        "params": {
            "agent_exists": "True",
            "agent_name": "agent",
            "entry_point": "evaluate",
            "environment_exists": "True",
            "environment_name": "environment",
            "root_name": "agent",
            "spec_is_frozen": "True",
        },
        "tags": {
            "mlflow.source.git.commit": (
                "73fbfe92028aec1a259935b5d809f1a7ee1e4336"
            ),
            "mlflow.source.name": "/home/nickj/agentos/env/bin/agentos",
            "mlflow.source.type": "LOCAL",
            "mlflow.user": "nickj",
            "run_type": "evaluate",
        },
    },
    "mlflow_info": {
        "artifact_uri": (
            "file:///home/nickj/agentos/example_agents/sb3_agent/mlruns/0/"
            "39be22d7ff9848bd9545988ff15f578f/artifacts"
        ),
        "end_time": 1639001190864,
        "experiment_id": "0",
        "lifecycle_stage": "active",
        "run_id": "39be22d7ff9848bd9545988ff15f578f",
        "run_uuid": "39be22d7ff9848bd9545988ff15f578f",
        "start_time": 1639001190314,
        "status": "FINISHED",
        "user_id": "nickj",
    },
    "parameter_set": {"agent": {"evaluate": {}}},
    "root_component": "agent",
}
