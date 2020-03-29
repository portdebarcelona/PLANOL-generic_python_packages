rem USER: __token__ y PASSWORD: el token creado en https://test.pypi.org/manage/account/#api-tokens

pushd "%~dp0../.."
pip install --user --upgrade twine
python -m twine upload --verbose --repository-url https://test.pypi.org/legacy/ dist/*
popd
