pushd "%~dp0../.."
pip install --user --upgrade setuptools wheel
python setup.py sdist bdist_wheel
popd