import json
import os
import re
import time
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import Optional

import urllib3
from dulwich import porcelain
from dulwich.errors import NotGitRepository
from dulwich.objectspec import parse_commit
from dulwich.refs import LOCAL_BRANCH_PREFIX
from dulwich.repo import Repo as PorcelainRepo

from pcs.exceptions import BadGitStateException
from pcs.utils import (
    AOS_GLOBAL_REPOS_DIR,
    clear_cache_path,
    parse_github_web_ui_url,
)


class GitManager:
    """
    This manager class wraps low-level git/dulwich operations.
    """

    FULL_GIT_SHA1_RE = re.compile(r"\b[0-9a-f]{40}\b")
    REPO_INFO_PROC_KEY = "process_id"
    REPO_INFO_TIME_KEY = "last_fetch_time"

    def get_public_url_and_hash(
        self, full_path: Path, force: bool
    ) -> (str, str):
        """
        Given a path to a a file or directory in a git repo, this returns a
        GitHub repo URL where the current version of the file or directory is
        publicly accessible AND the git hash of the current repo HEAD.  This
        will raise an exception if any of the following checks are true:

        1. The file/directory is not in a git repo.
        2. The origin of this repo is not GitHub.
        3. The current local commit is not in the remote repo.
        4. There are uncommitted changes locally

        If ''force'' is True, checks 2, 3, and 4 above are ignored.
        """

        try:
            porcelain_repo = PorcelainRepo.discover(full_path)
        except NotGitRepository:
            raise BadGitStateException(
                f"No git repo with Component found: {full_path}"
            )

        self._check_for_local_changes(porcelain_repo, force)
        url = self._check_for_github_url(porcelain_repo, force)
        curr_head_hash = self._check_remote_branch_status(
            porcelain_repo, force
        )
        return url, curr_head_hash

    def get_prefixed_path_from_repo_root(self, full_path: Path) -> Path:
        """
        Given a full, absolute path to a file or directory, returns a path
        relative to the innermost containing git repo.  For example, if
        ``component_path`` is::

            /foo/bar/baz/my_component.py

        and a git repo lives in::

            /foo/bar/.git/

        then this would return::

            baz/my_component.py
        """
        name = full_path.name
        curr_path = full_path.parent
        path_prefix = Path()
        while curr_path != Path(curr_path.root):
            try:
                PorcelainRepo(curr_path)
                return path_prefix / name
            except NotGitRepository:
                path_prefix = curr_path.name / path_prefix
                curr_path = curr_path.parent
        raise BadGitStateException(f"Unable to find repo: {full_path}")

    def get_sha1_from_version(
        self, org_name: str, project_name: str, version: str
    ) -> str:
        """
        Given a ``version`` (a full git sha1 commit hash, a branch name, or a
        tag name), returns the sha1 hash corresponding to that version.
        """
        match = re.match(self.FULL_GIT_SHA1_RE, version)
        if match:
            return match.group(0)
        # See if we're referring to a branch
        branches = self.get_branches(org_name, project_name)
        for branch in branches:
            if branch["name"] == version:
                return branch["commit"]["sha"]
        # See if we're referring to a tag
        tags = self.get_tags(org_name, project_name)
        for tag in tags:
            if tag["name"] == version:
                return tag["commit"]["sha"]
        error_msg = (
            f"Version {version} is not a full SHA1 hash and was "
            f"also not found in branches or tags"
        )
        raise BadGitStateException(error_msg)

    def _get_remote_url(
        self, porcelain_repo: PorcelainRepo, force: bool
    ) -> str:
        url_or_path = self._get_remote_uri(porcelain_repo, force)
        # If path, assume cloned from default repo and find default repo URL.
        if Path(url_or_path).exists():
            with porcelain.open_repo_closing(url_or_path) as local_repo:
                url = self._get_remote_uri(local_repo, force)
        else:
            url = url_or_path
        return url

    def _check_for_github_url(
        self, porcelain_repo: PorcelainRepo, force: bool
    ) -> str:
        url = self._get_remote_url(porcelain_repo, force)
        if url is None or "github.com" not in url:
            error_msg = f"Remote must be on github, not {url}"
            if force:
                print(f"Warning: {error_msg}")
            else:
                raise BadGitStateException(error_msg)
        return url

    def _get_remote_uri(
        self,
        porcelain_repo: PorcelainRepo,
        force: bool,
        remote_name: str = "origin",
    ) -> str:
        """Can return a local path string or a URL."""
        url = None
        try:
            REMOTE_KEY = (b"remote", remote_name.encode())
            url = porcelain_repo.get_config()[REMOTE_KEY][b"url"].decode()
        except KeyError:
            error_msg = "Could not find remote repo"
            if force:
                print(f"Warning: {error_msg}")
            else:
                raise BadGitStateException(error_msg)
        return url

    def _check_remote_branch_status(
        self, porcelain_repo: PorcelainRepo, force: bool
    ) -> str:
        curr_head_hash = porcelain_repo.head().decode()
        url = self._get_remote_url(porcelain_repo, force)
        project_name, repo_name, _, _ = parse_github_web_ui_url(url)
        remote_commit_exists = self.sha1_hash_exists(
            project_name, repo_name, curr_head_hash
        )
        if not remote_commit_exists:
            error_msg = (
                f"Current head hash {curr_head_hash} in "
                f"PCS repo {porcelain_repo} is not on remote {url}. "
                "Push your changes to your remote!"
            )
            if force:
                print(f"Warning: {error_msg}")
            else:
                raise BadGitStateException(error_msg)
        return curr_head_hash

    def _check_for_local_changes(
        self, porcelain_repo: PorcelainRepo, force: bool
    ) -> None:
        # Adapted from
        # https://github.com/dulwich/dulwich/blob/master/dulwich/porcelain.py#L1200
        # 1. Get status of staged
        tracked_changes = porcelain.get_tree_changes(porcelain_repo)
        # 2. Get status of unstaged
        index = porcelain_repo.open_index()
        normalizer = porcelain_repo.get_blob_normalizer()
        filter_callback = normalizer.checkin_normalize
        unstaged_changes = list(
            porcelain.get_unstaged_changes(
                index, porcelain_repo.path, filter_callback
            )
        )

        uncommitted_changes_exist = (
            len(unstaged_changes) > 0
            or len(tracked_changes["add"]) > 0
            or len(tracked_changes["delete"]) > 0
            or len(tracked_changes["modify"]) > 0
        )
        if uncommitted_changes_exist:
            print(
                f"\nUncommitted changes: {tracked_changes} or "
                f"{unstaged_changes}\n"
            )
            error_msg = "Commit all changes before freezing"
            if force:
                print(f"Warning: {error_msg}")
            else:
                raise BadGitStateException(error_msg)

    def _get_default_repo_path(self, org_name: str, project_name: str) -> Path:
        """
        We checkout a "default repo" to map ref names to sha1 hashes.
        """
        global_default_path = AOS_GLOBAL_REPOS_DIR / "_default"
        default_repo_path = global_default_path / org_name / project_name
        url = f"https://github.com/{org_name}/{project_name}.git"
        cloned = self._clone_repo(src=url, clone_destination=default_repo_path)
        if not cloned:
            self._maybe_fetch(default_repo_path)
        return default_repo_path

    def _write_repo_info(self, repo_path: Path) -> dict:
        default_info_path = self._get_repo_info_path(repo_path)
        repo_info = {
            self.REPO_INFO_PROC_KEY: os.getpid(),
            self.REPO_INFO_TIME_KEY: time.time(),
        }
        with open(default_info_path, "w") as fout:
            json.dump(repo_info, fout)
        return repo_info

    def _read_repo_info(self, repo_path: Path) -> Optional[dict]:
        default_info_path = self._get_repo_info_path(repo_path)
        with open(default_info_path) as fin:
            try:
                return json.load(fin)
            except JSONDecodeError:
                return None

    def _get_repo_info_path(self, repo_path: Path) -> Path:
        return Path(str(repo_path) + "-info.json")

    def _maybe_fetch(self, default_repo_path: Path) -> None:
        """
        This function periodically runs `git fetch` in the "default" repo used
        to map ref names to sha1 hashes.  We only update if we're a new
        process or if we haven't updated in the last half hour.
        """

        def _do_fetch():
            print(f"GitManager: fetching {default_repo_path}...")
            with porcelain.open_repo_closing(default_repo_path) as repo:
                try:
                    porcelain.fetch(repo)
                except urllib3.exceptions.MaxRetryError:
                    error_msg = (
                        "GitManager: couldn't contact GitHub "
                        f"to fetch {default_repo_path}..."
                    )
                    print(error_msg)
                    return
            self._write_repo_info(default_repo_path)

        info_path = self._get_repo_info_path(default_repo_path)
        assert info_path.exists()
        repo_info = self._read_repo_info(default_repo_path)
        if repo_info is None:
            _do_fetch()
            return
        if repo_info[self.REPO_INFO_PROC_KEY] != os.getpid():
            _do_fetch()
            return
        sec_since_last_fetch = time.time() - repo_info[self.REPO_INFO_TIME_KEY]
        if sec_since_last_fetch > 1800:
            _do_fetch()
            return
        print(f"GitManager: NOT fetching {default_repo_path}...")

    def clear_repo_cache(
        self, repo_cache_path: Path = None, assume_yes: bool = False
    ) -> None:
        """
        Completely removes all the repos that have been created or checked
        out in the ``repo_cache_path``. Pass True to ``assume_yes`` to run
        non-interactively.
        """
        repo_cache_path = repo_cache_path or AOS_GLOBAL_REPOS_DIR
        clear_cache_path(repo_cache_path, assume_yes)

    def clone_repo(
        self, org_name: str, project_name: str, version: str
    ) -> Path:
        """
        Given a GitHub org, project name, and version (a sha1 commit hash,
        branch name, or tag name), this will clone the repo at the version
        into the PCS/AOS cache.
        """
        sha1 = self.get_sha1_from_version(org_name, project_name, version)
        default_repo_path = self._get_default_repo_path(org_name, project_name)
        clone_destination = (
            AOS_GLOBAL_REPOS_DIR / org_name / project_name / sha1
        )
        self._clone_repo(
            src=default_repo_path,
            clone_destination=clone_destination,
            version=sha1,
        )
        return clone_destination

    def _clone_repo(
        self, src: str, clone_destination: Path, version: str = None
    ) -> bool:
        """``src`` can be a local file path or a GitHub URL."""
        cloned = False
        if not clone_destination.exists():
            clone_destination.mkdir(parents=True)
            print(f"GitManager: cloning {src} to {str(clone_destination)}")
            porcelain.clone(
                source=str(src), target=str(clone_destination), checkout=True
            )
            self._write_repo_info(clone_destination)
            if version:
                self._checkout_version(clone_destination, version)
            cloned = True
        assert clone_destination.exists(), f"Unable to clone {src}"
        info_path = self._get_repo_info_path(clone_destination)
        assert info_path.exists()
        return cloned

    def _checkout_version(self, local_repo_path: Path, version: str) -> None:
        curr_dir = os.getcwd()
        os.chdir(local_repo_path)
        with porcelain.open_repo_closing(local_repo_path) as repo:
            treeish = parse_commit(repo, version).sha().hexdigest()
            # Checks for a clean working directory were failing on Windows, so
            # force the checkout since this should be a clean clone anyway.
            self._checkout(repo=repo, target=treeish, force=True)
        os.chdir(curr_dir)

    def get_branches(self, org_name: str, project_name: str) -> list:
        """
        Returns all the branches found in the GitHub repo at:

        https://github.com/org_name/project_name

        The data structure returned mirrors that GitHub API and looks like
        the following:

        [
            {
                'name': <tag_name>
                'commit': {
                    'sha': <sha1_hash>
                }
            },
            ...
        ]

        """

        return self._get_refs_with_prefix(
            org_name, project_name, "refs/remotes/origin/"
        )

    def get_tags(self, org_name: str, project_name: str) -> list:
        """
        Returns all the tags found in the GitHub repo at:

        https://github.com/org_name/project_name

        The data structure returned mirrors that GitHub API and looks like
        the following:

        [
            {
                'name': <tag_name>
                'commit': {
                    'sha': <sha1_hash>
                }
            },
            ...
        ]

        """
        return self._get_refs_with_prefix(org_name, project_name, "refs/tags/")

    # https://github.com/jelmer/dulwich/pull/898
    def _checkout(
        self, repo: PorcelainRepo, target: bytes, force: bool = False
    ) -> None:
        """
        This code is taken from the currently unmerged (but partially
        cherry-picked) code in https://github.com/jelmer/dulwich/pull/898
        that adds checkout() functionality to the dulwich code base.

        Switch branches or restore working tree files
        Args:
          repo: dulwich Repo object
          target: branch name or commit sha to checkout
        """
        # check repo status
        if not force:
            index = repo.open_index()
            for file in porcelain.get_tree_changes(repo)["modify"]:
                if file in index:
                    raise Exception(
                        "trying to checkout when working directory not clean"
                    )

            normalizer = repo.get_blob_normalizer()
            filter_callback = normalizer.checkin_normalize

            unstaged_changes = list(
                porcelain.get_unstaged_changes(
                    index, repo.path, filter_callback
                )
            )
            for file in unstaged_changes:
                if file in index:
                    raise Exception(
                        "Trying to checkout when working directory not clean"
                    )

        current_tree = porcelain.parse_tree(repo, repo.head())
        target_tree = porcelain.parse_tree(repo, target)

        # update head
        if (
            target == b"HEAD"
        ):  # do not update head while trying to checkout to HEAD
            target = repo.head()
        elif target in repo.refs.keys(base=LOCAL_BRANCH_PREFIX):
            porcelain.update_head(repo, target)
            target = repo.refs[LOCAL_BRANCH_PREFIX + target]
        else:
            porcelain.update_head(repo, target, detached=True)

        # unstage files in the current_tree or target_tree
        tracked_changes = []
        for change in repo.open_index().changes_from_tree(
            repo.object_store, target_tree.id
        ):
            file = (
                change[0][0] or change[0][1]
            )  # no matter the file is added, modified or deleted.
            try:
                current_entry = current_tree.lookup_path(
                    repo.object_store.__getitem__, file
                )
            except KeyError:
                current_entry = None
            try:
                target_entry = target_tree.lookup_path(
                    repo.object_store.__getitem__, file
                )
            except KeyError:
                target_entry = None

            if current_entry or target_entry:
                tracked_changes.append(file)
        tracked_changes = [tc.decode("utf-8") for tc in tracked_changes]
        repo.unstage(tracked_changes)

        # reset tracked and unstaged file to target
        normalizer = repo.get_blob_normalizer()
        filter_callback = normalizer.checkin_normalize
        unstaged_files = porcelain.get_unstaged_changes(
            repo.open_index(), repo.path, filter_callback
        )
        saved_repo_path = repo.path
        repo.path = str(repo.path)
        for file in unstaged_files:
            file_path = Path(repo.path) / file.decode()
            file_path.parent.mkdir(parents=True, exist_ok=True)
            porcelain.reset_file(repo, file.decode(), b"HEAD")
        repo.path = saved_repo_path

        # remove the untracked file which in the current_file_set
        for file in porcelain.get_untracked_paths(
            repo.path, repo.path, repo.open_index(), exclude_ignored=True
        ):
            # TODO: Code below is from the original dulwich PR; had trouble
            # getting this to work on Windows; Untracked files sitting in repo
            # weren't being properly removed. Went with a more direct approach.
            #
            # try:
            #     current_tree.lookup_path(
            #         repo.object_store.__getitem__, file.encode()
            #     )
            # except KeyError:
            #     pass
            # else:
            #     os.remove(os.path.join(repo.path, file))

            full_path = Path(repo.path) / Path(file)
            if full_path.exists():
                os.remove(full_path)

    def _get_refs_with_prefix(
        self, org_name: str, project_name: str, prefix: str
    ) -> list:
        default_repo_path = self._get_default_repo_path(org_name, project_name)
        with porcelain.open_repo_closing(default_repo_path) as repo:
            refs = repo.get_refs()
            results = []
            for ref, sha1_hash in refs.items():
                ref = ref.decode()
                if not ref.startswith(prefix):
                    continue
                name = ref.replace(prefix, "", 1)
                results.append(
                    {"name": name, "commit": {"sha": sha1_hash.decode()}}
                )
            return results

    def sha1_hash_exists(
        self, org_name: str, project_name: str, sha1_hash: str
    ) -> bool:
        """
        Checks if ``sha1_hash`` exists in the repo at:

        https://github.com/<org_name>/<project_name>
        """
        default_repo_path = self._get_default_repo_path(org_name, project_name)
        with porcelain.open_repo_closing(default_repo_path) as repo:
            try:
                repo[sha1_hash.encode()]
            except KeyError:
                return False
            return True
