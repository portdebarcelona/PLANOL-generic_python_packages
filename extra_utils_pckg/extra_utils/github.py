import json
import os
import shutil
from tempfile import mkdtemp
from urllib.request import Request, urlopen

from extra_utils.misc import download_and_unzip, remove_content_dir

FILE_LAST_TAG_REPO = 'last_tag_repo.txt'


def request_api_github(owner, repo, api_request, token=None):
    """

    Args:
        owner (str):
        repo (str):
        api_request (str):
        token (str=None):

    Returns:
        info_response (dict)
    """
    request_headers = {
        'Accept': 'application/vnd.github.v3+json'
    }
    if token:
        request_headers['Authorization'] = f'token {token}'

    url_github = f'https://api.github.com/repos/{owner}/{repo}/{api_request}'
    req = Request(url_github, headers=request_headers, method='GET')
    info_response = {}
    with urlopen(req) as resp_request:
        if resp_request:
            info_response = json.load(resp_request)

    return info_response


def update_repo_github(html_repo, tag, name_zip, path_repo, header=None, force_update=False, remove_prev=False):
    """
    
    Args:
        html_repo (str):
        tag (str):
        name_zip (str):
        path_repo (str):
        header (dict=None):
        force_update (bool=False):
        remove_prev (bool=False):

    Returns:
        updated (bool)
    """
    updated = False
    log_last_tag = os.path.join(path_repo, FILE_LAST_TAG_REPO)

    if not force_update:
        last_tag = None
        if os.path.exists(log_last_tag):
            with open(log_last_tag) as fr:
                last_tag = fr.read()

        if last_tag and last_tag.strip() == tag.strip():
            return updated

    if not header:
        header = {}
    header['Accept'] = 'application/octet-stream'

    dir_temp = mkdtemp()
    download_and_unzip(html_repo,
                       extract_to=dir_temp,
                       headers=[(k, v) for k, v in header.items()])
    path_res = os.path.join(dir_temp, name_zip)

    if os.path.exists(path_res):
        if remove_prev and os.path.exists(path_repo):
            remove_content_dir(path_repo)
        shutil.copytree(path_res, path_repo, dirs_exist_ok=True)
        shutil.rmtree(path_res, ignore_errors=True)

        with open(log_last_tag, "w+") as fw:
            fw.write(tag)

        updated = True

    return updated


def download_latest_release_repo_github(owner, repo, download_to, token=None, force=False):
    """

    Args:
        owner (str):
        repo (str):
        download_to (str):
        token (str=None):
        force (bool=False):

    Returns:
        tag_name (str)
    """
    info_latest_release = request_api_github(owner, repo, 'releases/latest', token)

    tag_name = info_latest_release.get('tag_name')
    if tag_name:
        html_release = f'https://github.com/{owner}/{repo}/archive/refs/tags/{tag_name}.zip'
        header = {}
        if token:
            header['Authorization'] = f'token {token}'

        update_repo_github(html_release, tag_name, f'{repo}-{tag_name}', download_to,
                           header=header, force_update=force, remove_prev=force)

        return tag_name


def download_branch_repo_github(owner, repo, branch, download_to, token=None, force=False):
    """

    Args:
        owner (str):
        repo (str):
        branch (str):
        download_to (str):
        token (str=None):
        force (bool=False):

    Returns:
        sha_commit (str)
    """
    branch = branch.lower()
    info_branches = request_api_github(owner, repo, 'branches', token)
    info_branch = next(filter(lambda el: el.get('name', '').lower() == branch, 
                              info_branches), None)

    if info_branch:
        sha_commit = info_branch.get('commit').get('sha')
        html_branch = f'https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip'
        header = {}
        if token:
            header['Authorization'] = f'token {token}'

        update_repo_github(html_branch, sha_commit, f'{repo}-{branch}', download_to,
                           header=header, force_update=force, remove_prev=force)

        return sha_commit
