#!/bin/bash

brew install wget
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -O ~/miniconda.sh
bash ~/miniconda.sh -b -p ${HOME}/miniconda
source "${HOME}/miniconda/bin/activate"
conda init bash
conda init zsh