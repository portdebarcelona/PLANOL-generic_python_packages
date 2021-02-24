pushd "%~dp0../.."
pip install --user --upgrade setuptools wheel
python setup.py install
popd