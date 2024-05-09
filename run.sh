#!/bin/bash
cd `dirname $0`

MODULE_DIR=$(dirname $0)
VIRTUAL_ENV=$MODULE_DIR/.venv
PYTHON=$VIRTUAL_ENV/bin/python
SUDO=sudo
EXTRA=

if ! command -v $SUDO; then
  echo "no sudo on this system, proceeding as current user"
  SUDO=""
fi

if command -v apt-get; then
  if dpkg -s python3-venv; then
    echo "python3-venv is installed, skipping setup"
  else
    if ! apt info python3-venv; then
      echo "package info not found, trying apt update"
      $SUDO apt-get -qq update
    fi
    $SUDO apt-get install -qqy python3-venv cmake make
  fi
else
  echo "Skipping tool installation because your platform is missing apt-get"
  echo "If you see failures below, install the equivalent of python3-venv for your system"
fi

OS=$(uname)
if [[ $OS == "Linux" ]]; then
  echo "Running on Linux"

  if command -v clinfo; then
    echo "Setting OpenCL BLAS cmake args"
    export CMAKE_ARGS="-DLLAMA_CLBLAST=on"
  elif command -v nvidia-smi; then
    echo "Setting Cuda BLAS cmake args"
    export CMAKE_ARGS="-DLLAMA_CUDA=on"
    export CUDACXX=/usr/local/cuda/bin/nvcc
    CUDA_VER=$(nvidia-smi | grep "CUDA Version" | awk '{print $(NF-1)}' | tr -d '.')
    EXTRA="--extra-index-url https://abetlen.github.io/llama-cpp-python/whl/$CUDA_VER"
  else
    echo "Setting OpenBLAS cmake args"
    $SUDO apt-get install -qqy clang libopenblas-dev
    export CC="clang"
    export CXX="clang"
    export CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS"
    EXTRA="--extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu"
  fi
fi

if [[ $OS == "Darwin" ]]; then
  echo "Running on MacOS"
  echo "Setting Metal cmake args"
  export CMAKE_ARGS="-DLLAMA_METAL=on"
  EXTRA="--extra-index-url https://abetlen.github.io/llama-cpp-python/whl/metal"
fi

if [ ! -d "$VIRTUAL_ENV" ]; then
  echo "creating virtualenv at $VIRTUAL_ENV"
  python3 -m venv $VIRTUAL_ENV
fi

source $VIRTUAL_ENV/bin/activate

if [ ! -f .installed ]; then
  pip3 install --upgrade --force-reinstall --no-cache-dir llama-cpp-python $EXTRA
  pip3 install --upgrade -r requirements.txt

  if [ $? -eq 0 ]; then
    touch .installed
  fi
fi

mkdir -p ~/.data/models
export MODEL_DIR="$HOME/.data/models"

exec $PYTHON -m src $@

