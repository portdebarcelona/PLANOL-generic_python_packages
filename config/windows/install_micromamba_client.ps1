# destino dentro del perfil de usuario
$dest = Join-Path $Env:USERPROFILE 'micromamba'
if (-not (Test-Path $dest)) {
    New-Item -ItemType Directory -Path $dest -Force | Out-Null
}

$archive = Join-Path $dest 'micromamba.tar.bz2'

# descargar directamente en la carpeta de usuario
Invoke-WebRequest -URI 'https://micro.mamba.pm/api/micromamba/win-64/latest' -OutFile $archive

# extraer en la carpeta destino
tar -xf $archive -C $dest

# mover el ejecutable al raíz de la carpeta destino
$srcExe = Join-Path $dest 'Library\bin\micromamba.exe'
$dstExe = Join-Path $dest 'micromamba.exe'
Move-Item -Force $srcExe $dstExe

# ejecutar el binario desde la ruta absoluta para comprobar
& $dstExe --help

# usar la carpeta de usuario como MAMBA_ROOT_PREFIX
$Env:MAMBA_ROOT_PREFIX = $dest

[Environment]::SetEnvironmentVariable("MAMBA_ROOT_PREFIX", $dest, "User")

# Inicializar la shell
& $dstExe shell init -s powershell -r $Env:MAMBA_ROOT_PREFIX
& $dstExe shell init -s cmd.exe -r $Env:MAMBA_ROOT_PREFIX

# limpiar archivo temporal
Remove-Item -Force $archive
