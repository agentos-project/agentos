import json
import os

import requests
from pcs.utils import AOS_ROOT


class GitHubAPIManager:
    TOKEN_NAME = "GITHUB_AUTH_TOKEN"
    PRINTED_UNAUTHED = False

    def __init__(self):
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        token = self._get_token()
        if token:
            self.headers.update(
                {
                    "Authorization": f"token {token}",
                }
            )
        else:
            self._print_unauthed_message()

    def _print_unauthed_message(self):
        if GitHubAPIManager.PRINTED_UNAUTHED:
            return
        msg = (
            f"Couldn't find a GitHub auth token in {AOS_ROOT}/.env\n"
            f'as "{self.TOKEN_NAME}=<token>" or as an environment variable\n'
            f"{self.TOKEN_NAME}.  We will use the API unauthed but be aware\n"
            "GitHub has strict limits for unauthed requests.  Avoid these\n"
            "by creating a new auth token at: \n\n"
            "\thttps://github.com/settings/tokens/new\n\n"
            'The token must have the "repo"/"Full control of private\n'
            'repositories" permission if you want to use it against your\n'
            "own private repos. Make your token available in one of the\n"
            "above places to automatically start using the authed API."
        )
        print(f"\n{msg}\n")
        GitHubAPIManager.PRINTED_UNAUTHED = True

    def _get_token(self):
        env_file = AOS_ROOT / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f.readlines():
                    split_line = line.split("=")
                    if split_line[0] == self.TOKEN_NAME:
                        return split_line[1]
        else:
            if self.TOKEN_NAME in os.environ:
                return os.environ[self.TOKEN_NAME]

    def get_branches(self, project_name, repo_name):
        branch_url = (
            f"https://api.github.com/repos/{project_name}"
            f"/{repo_name}/branches"
        )
        response = requests.get(branch_url, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Problem with GitHub API: {response.content}")
        return json.loads(response.content)

    def get_tags(self, project_name, repo_name):
        tags_url = (
            f"https://api.github.com/repos/{project_name}" f"/{repo_name}/tags"
        )
        response = requests.get(tags_url, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Problem with GitHub API: {response.content}")
        return json.loads(response.content)

    def sha1_hash_exists(self, project_name, repo_name, sha1_hash):
        hash_url = (
            f"https://api.github.com/repos/{project_name}/{repo_name}"
            f"/commits/{sha1_hash}"
        )
        response = requests.get(hash_url, headers=self.headers)
        if response.status_code == 422:
            return False
        elif response.status_code == 200:
            return True
        else:
            raise Exception(f"Problem with GitHub API: {response.content}")
