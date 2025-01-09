#!/bin/sh

#  The script is pretty straightforward. It installs the required dependencies, builds the package, and uploads it to the specified repository.
#  The script takes three arguments:
#     PACKAGE_FOLDER  - the folder where the package is located
#     PYPI_API_TOKEN  - the API token for the repository
#     REPOSITORY  - the repository where the package will be uploaded (default is  pypi )
#  The script uses the  twine  package to upload the package to the repository. The  TWINE_USERNAME  and  TWINE_PASSWORD  environment variables are set to  __token__  and the API token, respectively.
#  The  --non-interactive  flag is used to prevent the script from asking for confirmation before uploading the package.
#  Step 3: Create a GitHub Action
#  Now that we have the script ready, we can create a GitHub Action to automate the process of building and uploading the package.
#  Create a new file named  build_pckg.yml  in the  .github/workflows  directory.

if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 <PACKAGE_FOLDER> <PYPI_API_TOKEN> [repository]"
  exit 1
fi

PACKAGE_FOLDER=$1
PYPI_API_TOKEN=$2
REPOSITORY=${3:-pypi}

# Set the current directory on the folder where this script is located
cd "$(dirname "$0")" || exit

pip install -r requirements.txt

cd "$PACKAGE_FOLDER" || exit

# Set the environment variable GIT_REPO to null to not use it
export GIT_REPO="null"

python -m build
twine upload --username __token__ --password "$PYPI_API_TOKEN" --verbose --non-interactive -r "$REPOSITORY" dist/*
