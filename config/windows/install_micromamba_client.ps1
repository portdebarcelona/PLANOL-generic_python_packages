Invoke-Webrequest -URI https://micro.mamba.pm/api/micromamba/win-64/latest -OutFile micromamba.tar.bz2
tar xf micromamba.tar.bz2

MOVE -Force Library\bin\micromamba.exe micromamba.exe
.\micromamba.exe --help

# You can use e.g. $HOME\micromambaenv as your base prefix
$Env:MAMBA_ROOT_PREFIX="$Env:USERPROFILE\micromamba"

# Invoke the hook
.\micromamba.exe shell hook -s powershell | Out-String | Invoke-Expression

# ... or initialize the shell
.\micromamba.exe shell init -s powershell -p $Env:MAMBA_ROOT_PREFIX
