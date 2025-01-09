import functools
import json
import os
import shutil
from tempfile import mkdtemp
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from apb_extra_utils.misc import download_and_unzip, remove_content_dir, zip_dir, create_dir

PREFIX_FILE_LAST_TAG_REPO = 'last_tag_repo_github_'


def get_api_github(owner, repo, api_request, token=None):
    """
    GET Request for repository GITHUB via API GITHUB.

    See the REST API DOCS here https://docs.github.com/en/rest

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
    try:
        with urlopen(req) as resp_request:
            if resp_request:
                info_response = json.load(resp_request)
    except HTTPError as exc:
        info_response[HTTPError.__name__] = str(exc)

    return info_response


def post_api_github(owner, repo, api_request, post_data, token=None):
    """
    POST Request on repository GITHUB via API GITHUB

    See the REST API DOCS here https://docs.github.com/en/rest

    Args:
        owner (str):
        repo (str):
        api_request (str):
        post_data (dict):
        token (str=None):

    Returns:
        info_response (dict)
    """
    request_headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json; charset=utf-8',
    }
    if token:
        request_headers['Authorization'] = f'token {token}'

    url_github = f'https://api.github.com/repos/{owner}/{repo}/{api_request}'

    post_data_enc = json.dumps(post_data).encode('utf-8')

    req = Request(url_github, headers=request_headers, method='POST')
    info_response = {}
    try:
        with urlopen(req, post_data_enc) as resp_request:
            if resp_request:
                info_response = resp_request.__dict__
    except HTTPError as exc:
        info_response[HTTPError.__name__] = str(exc)

    return info_response


@functools.cache
def has_changes_in_github(owner, repo, branch, download_to, token=None):
    """
    Check if the GitHub repository branch has changes.
    
    Args:
        owner (str): Owner repository Github
        repo (str): Name repository Github
        branch (str): Branch repository to check
        download_to (str): Path to the local repository
        token (str=None): Github token for private access

    Returns:
        bool: True if there are changes, False otherwise
        str: sha_commit of the current branch state
    """
    branch = branch.lower()
    info_branches = get_api_github(owner, repo, 'branches', token)
    info_branch = next(filter(lambda el: el.get('name', '').lower() == branch,
                              info_branches), None)

    if not info_branch:
        return False, None

    sha_commit = info_branch.get('commit').get('sha')
    expected_name_zip_repo = f'{repo}-{branch}'
    log_last_tag = os.path.join(download_to, f'.{PREFIX_FILE_LAST_TAG_REPO}{expected_name_zip_repo}')

    if os.path.exists(log_last_tag):
        with open(log_last_tag) as fr:
            last_tag = fr.read()
            if last_tag and last_tag.strip() == sha_commit.strip():
                return False, sha_commit

    return True, sha_commit


def get_resources_from_repo_github(html_repo, tag, expected_name_zip_repo, path_repo, header=None,
                                   force_update=False, remove_prev=False, as_zip=False):
    """
    
    Args:
        html_repo (str):
        tag (str):
        expected_name_zip_repo (str):
        path_repo (str):
        header (dict=None):
        force_update (bool=False):
        remove_prev (bool=False):
        as_zip (bool=False):

    Returns:
        updated (bool)
    """
    updated = False
    log_last_tag = os.path.join(path_repo, f'.{PREFIX_FILE_LAST_TAG_REPO}{expected_name_zip_repo}')

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
    download_and_unzip(html_repo, extract_to=dir_temp, headers=[(k, v) for k, v in header.items()])
    path_res = os.path.join(dir_temp, expected_name_zip_repo)

    if os.path.exists(path_res):
        create_dir(path_repo)

        if as_zip:
            zip_dir(path_res, os.path.join(path_repo, f'{expected_name_zip_repo}.zip'))
        else:
            if remove_prev and os.path.exists(path_repo):
                remove_content_dir(path_repo)
            shutil.copytree(path_res, path_repo, dirs_exist_ok=True)

        shutil.rmtree(path_res, ignore_errors=True)

        with open(log_last_tag, "w+") as fw:
            fw.write(tag)

        updated = True

    return updated


def download_release_repo_github(owner, repo, download_to, tag_release=None, token=None, force=False, as_zip=False,
                                 remove_prev=False):
    """
    Download release Github repository on the path selected.

    Args:
        owner (str): Owner repository Github
        repo (str): Name repository Github
        download_to (str): Path to download
        tag_release (str=None): if not informed get 'latest' release
        token (str=None): Github token for private access
        force (bool=False): Force update if exists previous sources
        remove_prev (bool=False): Remove all previous resources
        as_zip (bool=False): Retorna como ZIP

    Returns:
        tag_name (str)
    """
    if not tag_release:
        info_release = get_api_github(owner, repo, 'releases/latest', token)
    else:
        info_release = get_api_github(owner, repo, f'releases/tags/{tag_release}', token)

    tag_name = info_release.get('tag_name')
    if tag_name:
        html_release = f'https://github.com/{owner}/{repo}/archive/refs/tags/{tag_name}.zip'
        header = {}
        if token:
            header['Authorization'] = f'token {token}'

        get_resources_from_repo_github(html_release, tag_name, f'{repo}-{tag_name}', download_to,
                                       header=header, force_update=force, remove_prev=remove_prev, as_zip=as_zip)

        return tag_name


def download_branch_repo_github(owner, repo, branch, download_to, token=None, force=False, as_zip=False,
                                remove_prev=False):
    """
    Download the branch selected for the Github repo on the path selected

    Args:
        owner (str): Owner repository Github
        repo (str): Name repository Github
        branch (str): Branch repository to download
        download_to (str): Path to download
        token (str=None): Github token for private access
        force (bool=False): Force update if exists previous sources
        remove_prev (bool=False): Remove all previous resources
        as_zip (bool=False): Retorna como ZIP

    Returns:
        sha_commit (str), updated (boolean)
    """
    has_changes, sha_commit = has_changes_in_github(owner, repo, branch, download_to, token)
    if not has_changes and not force:
        return sha_commit, False
    html_branch = f'https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip'
    header = {}
    if token:
        header['Authorization'] = f'token {token}'

    name_zip = f'{repo}-{branch}'
    updated = get_resources_from_repo_github(html_branch, sha_commit, name_zip, download_to,
                                             header=header, force_update=force, remove_prev=remove_prev, as_zip=as_zip)

    if as_zip:
        path_zip = os.path.join(download_to, f'{name_zip}.zip')
        if os.path.exists(path_zip):
            new_path_zip = os.path.join(download_to, f'{name_zip}-{sha_commit}.zip')
            if os.path.exists(new_path_zip):
                os.remove(new_path_zip)
            os.rename(path_zip, new_path_zip)

    return sha_commit, updated


if __name__ == '__main__':
    import fire, sys

    sys.exit(fire.Fire(
        {
            get_api_github.__name__: get_api_github,
            post_api_github.__name__: post_api_github,
            download_release_repo_github.__name__: download_release_repo_github,
            download_branch_repo_github.__name__: download_branch_repo_github
        }
    ))
