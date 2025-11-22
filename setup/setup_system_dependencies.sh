#!/bin/bash

# System Dependencies Setup Script
# Supports macOS and Ubuntu systems

set -e  # Exit on any error

MINICONDA_DIR="$HOME/miniconda3"
CONDA_ENV="rnable"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Check if it's Ubuntu
        if command_exists lsb_release; then
            if lsb_release -is | grep -q "Ubuntu"; then
                echo "ubuntu"
            else
                echo "unknown_linux"
            fi
        else
            # Fallback: check /etc/os-release
            if [[ -f /etc/os-release ]]; then
                if grep -q "Ubuntu" /etc/os-release; then
                    echo "ubuntu"
                else
                    echo "unknown_linux"
                fi
            else
                echo "unknown_linux"
            fi
        fi
    else
        echo "unknown"
    fi
}

# Function to install homebrew on macOS
install_homebrew() {
    if command_exists brew; then
        print_status "Homebrew is already installed. Updating..."
        brew update
        print_success "Homebrew updated successfully"
    else
        print_status "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Add Homebrew to PATH for current session
        if [[ -f "/opt/homebrew/bin/brew" ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [[ -f "/usr/local/bin/brew" ]]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi

        print_success "Homebrew installed successfully"
    fi
}

# Function to update apt on Ubuntu
update_apt() {
    print_status "Updating apt package list..."
    sudo apt update
    print_success "apt updated successfully"
}

# Function to install Miniconda
install_miniconda() {
    local MINICONDA_URL
    if [[ "$OS" == "macos" ]]; then
        if [[ $(uname -m) == "arm64" ]]; then
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh"
        else
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
        fi
    else
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    fi

    if [[ -d "$MINICONDA_DIR" ]]; then
        print_status "Miniconda already installed at $MINICONDA_DIR"
    else
        print_status "Installing Miniconda..."
        wget -O /tmp/miniconda.sh "$MINICONDA_URL"
        bash /tmp/miniconda.sh -b -p "$MINICONDA_DIR"
        rm /tmp/miniconda.sh
        print_success "Miniconda installed successfully"
    fi

    print_status "Initializing conda..."
    source "$MINICONDA_DIR/bin/activate"
    conda init bash
    source ~/.bashrc 2>/dev/null || source ~/.bash_profile 2>/dev/null || true

    print_status "Updating conda base environment..."
    conda update -n base -c defaults conda -y

    print_status "Creating rnable conda environment with required packages..."
    conda env list | grep -q "^$CONDA_ENV" >/dev/null 2>&1 || {
        conda create -n "$CONDA_ENV" -y -c conda-forge \
            python=3.10 \
            r-base=4.4 \
            r-biocmanager \
            rpy2 \
            jq \
            zlib \
            dash \
            plotly \
            pandas \
            scikit-learn \
            matplotlib \
            libstdcxx-ng \
            postgresql
    }

    print_status "Activating rnable environment..."
    source "$MINICONDA_DIR/bin/activate"
    conda activate "$CONDA_ENV"

    print_success "Miniconda setup complete"
}

# Function to install pyenv
install_pyenv() {
    if command_exists pyenv; then
        print_status "pyenv is already installed. Skipping..."
        return
    fi

    print_status "Installing pyenv..."

    conda install -n "$CONDA_ENV" -y -c conda-forge pyenv

    # Add pyenv to shell configuration
    SHELL_RC=""
    if [[ "$SHELL" == *"zsh"* ]]; then
        SHELL_RC="$HOME/.zshrc"
    else
        SHELL_RC="$HOME/.bashrc"
    fi

    print_status "Adding pyenv configuration to $SHELL_RC..."

    # Check if pyenv configuration already exists
    if ! grep -q "PYENV_ROOT" "$SHELL_RC"; then
        echo 'export PYENV_ROOT="$HOME/.pyenv"' >> "$SHELL_RC"
        echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> "$SHELL_RC"

        if [[ "$SHELL" == *"zsh"* ]]; then
            echo 'eval "$(pyenv init - zsh)"' >> "$SHELL_RC"
        else
            echo 'eval "$(pyenv init - bash)"' >> "$SHELL_RC"
        fi

        print_success "pyenv configuration added to $SHELL_RC"
    else
        print_status "pyenv configuration already exists in $SHELL_RC"
    fi

    # Export pyenv for current session
    export PYENV_ROOT="$HOME/.pyenv"
    [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"

    if [[ "$SHELL" == *"zsh"* ]]; then
        eval "$(pyenv init - zsh)"
    else
        eval "$(pyenv init - bash)"
    fi

    print_success "pyenv installed successfully"
}

# Function to install pipx
install_pipx() {
    if command_exists pipx; then
        print_status "pipx is already installed. Skipping..."
    else
        print_status "Installing pipx..."

        conda install -n "$CONDA_ENV" -y -c conda-forge pipx
        print_success "pipx installed successfully"
    fi

    print_status "Ensuring pipx is in PATH..."
    pipx ensurepath
    print_success "pipx PATH configuration completed"
}

# Function to install Poetry
install_poetry() {
    if command_exists poetry; then
        print_status "Poetry is already installed. Skipping..."
    else
        print_status "Installing Poetry..."
        conda install -n "$CONDA_ENV" -y -c conda-forge poetry
        print_success "Poetry installed successfully"
    fi
}

# Function to install poetry shell
install_poetry_shell() {
    if command_exists poetry shell; then
        print_status "poetry shell is already installed. Skipping..."
    else
        print_status "Installing poetry shell..."
        poetry self add poetry-plugin-shell
        print_success "poetry shell installed successfully"
    fi
}

# Function to install pre-commit
install_precommit() {
    if command_exists pre-commit; then
        print_status "pre-commit is already installed. Skipping..."
    else
        print_status "Installing pre-commit..."
        conda install -n "$CONDA_ENV" -y -c conda-forge pre-commit
        print_success "pre-commit installed successfully"
    fi
}

# Function to install PostgreSQL
install_postgres() {
    if command_exists psql; then
        print_status "PostgreSQL is already installed. Skipping..."
    else
        print_status "Installing PostgreSQL into the rnable env..."
        conda install -n "$CONDA_ENV" -y -c conda-forge postgresql
        print_warning "PostgreSQL client installed inside rnable env; system-level service start is not handled by this script"
        print_success "PostgreSQL client installed successfully"
    fi
}



# Function to initialize pre-commit
init_precommit() {
    print_status "Initializing pre-commit..."
    pre-commit install
    print_success "pre-commit initialized successfully"
}

# Main execution
main() {
    print_status "Starting system dependencies setup..."

    # Detect operating system
    OS=$(detect_os)
    print_status "Detected OS: $OS"

    # Check if OS is supported
    if [[ "$OS" != "macos" && "$OS" != "ubuntu" ]]; then
        print_error "Unsupported operating system: $OS"
        print_error "This script only supports macOS and Ubuntu"
        exit 1
    fi

    # Update package managers
    if [[ "$OS" == "macos" ]]; then
        install_homebrew
    elif [[ "$OS" == "ubuntu" ]]; then
        update_apt
    fi

    # Install dependencies
    install_miniconda
    install_pyenv
    install_pipx
    install_poetry
    install_poetry_shell
    install_precommit
    init_precommit
    install_postgres

    print_success "All dependencies have been installed successfully!"
    print_warning "Note: You may need to restart your shell or run 'source ~/.bashrc' (or ~/.zshrc) to use pyenv"
    print_warning "For PostgreSQL, you may need to start the service manually"
}

# Run main function
main "$@"
