#!/bin/bash

# --- Functions ---

show_welcome() {
    clear  # Clear the screen for a clean look

    echo ""
    sleep 0.2
    echo " _   _      _ _          ____    _    __  __ ____           _ "
    sleep 0.2
    echo "| | | | ___| | | ___    / ___|  / \  |  \/  |  _ \ ___ _ __| |"
    sleep 0.2
    echo "| |_| |/ _ \ | |/ _ \  | |     / _ \ | |\/| | |_) / _ \ '__| |"
    sleep 0.2
    echo "|  _  |  __/ | | (_) | | |___ / ___ \| |  | |  __/  __/ |  |_|"
    sleep 0.2
    echo "|_| |_|\___|_|_|\___/   \____/_/   \_\_|  |_|_|   \___|_|  (_)"
    sleep 0.5

    echo ""
    echo "🌲🏕️     WELCOME TO CAMP SETUP! 🏕️   🌲"
    echo "===================================================="
    echo ""
    echo "   🏕️     Configuring Databases & Conda Environments"
    echo "       for CAMP short-read taxonomy"
    echo ""
    echo "   🔥 Let's get everything set up properly!"
    echo ""
    echo "===================================================="
    echo ""

}

# Check to see if the base CAMP environment has already been installed 
find_install_camp_env() {
    if conda env list | grep -q "$DEFAULT_CONDA_ENV_DIR/camp"; then 
        echo "✅ The main CAMP environment is already installed in $DEFAULT_CONDA_ENV_DIR."
    else
        echo "🚀 Installing the main CAMP environment in $DEFAULT_CONDA_ENV_DIR/..."
        conda create --prefix "$DEFAULT_CONDA_ENV_DIR/camp" -c conda-forge -c bioconda biopython blast bowtie2 bumpversion click click-default-group cookiecutter jupyter matplotlib numpy pandas samtools scikit-learn scipy seaborn snakemake umap-learn upsetplot
        echo "✅ The main CAMP environment has been installed successfully!"
    fi
}

# Check to see if the required conda environments have already been installed 
find_install_conda_env() {
    if conda env list | grep -q "$DEFAULT_CONDA_ENV_DIR/$1"; then
        echo "✅ The $1 environment is already installed in $DEFAULT_CONDA_ENV_DIR."
    else
        echo "🚀 Installing $1 in $DEFAULT_CONDA_ENV_DIR/$1..."
        conda create --prefix $DEFAULT_CONDA_ENV_DIR/$1 -c conda-forge -c bioconda $1
        echo "✅ $1 installed successfully!"
}

# Install databases in the specified directory
ask_taxonomy_db() {
    local TOOL_NAME="$1"
    local DB_VAR_NAME="$2"
    local DEFAULT_DB_DIR="$HOME/databases/$TOOL_NAME"
    local INSTALL_DIR=""
    local DB_PATH=""

    echo "🧬 Setting up database for $TOOL_NAME..."

    while true; do
        read -p "❓ Do you already have the $TOOL_NAME database installed? (y/n): " RESPONSE
        case "$RESPONSE" in
            [Yy]* )
                read -p "📂 Enter the full path to your existing $TOOL_NAME database: " DB_PATH
                if [[ -d "$DB_PATH" ]]; then
                    DATABASE_PATHS["$DB_VAR_NAME"]="$DB_PATH"
                    echo "✅ $TOOL_NAME DB path set to: $DB_PATH"
                else
                    echo "⚠️ Invalid path provided. Please verify and update parameters.yaml manually later."
                fi
                return
                ;;
            [Nn]* )
                while true; do
                    read -p "📥 Would you like to download and install the $TOOL_NAME database now? (y/n): " INSTALL
                    case "$INSTALL" in
                        [Yy]* )
                            read -p "📁 Enter install directory [default: $DEFAULT_DB_DIR]: " INSTALL_DIR
                            INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_DB_DIR}"
                            mkdir -p "$INSTALL_DIR"
                            echo "📡 Downloading $TOOL_NAME DB to $INSTALL_DIR ..."

                            if [[ "$TOOL_NAME" == "MetaPhlAn" ]]; then
                                wget -c https://s3.us-east-1.wasabisys.com/camp-databases/v0.1.1/taxonomy/metaphlan_20220926.tar.gz -P "$INSTALL_DIR"
                                tar -zxvf "$INSTALL_DIR/metaphlan_20220926.tar.gz" -C "$INSTALL_DIR"
                                rm "$INSTALL_DIR/metaphlan_20220926.tar.gz"
                                DB_PATH="$INSTALL_DIR/metaphlan_20220926"

                            elif [[ "$TOOL_NAME" == "Kraken2" ]]; then
                                echo "⚠️ Note: The Wasabi Kraken2 database may be incomplete. Prefer the official Kraken2 build if needed."
                                wget -c https://s3.us-east-1.wasabisys.com/camp-databases/v0.1.1/taxonomy/Kraken2.tar.gz -P "$INSTALL_DIR"
                                tar -zxvf "$INSTALL_DIR/Kraken2.tar.gz" -C "$INSTALL_DIR"
                                rm "$INSTALL_DIR/Kraken2.tar.gz"
                                DB_PATH="$INSTALL_DIR/Kraken2"

                            else
                                echo "❌ Unsupported tool: $TOOL_NAME"
                                return
                            fi

                            DATABASE_PATHS["$DB_VAR_NAME"]="$DB_PATH"
                            echo "✅ $TOOL_NAME DB installed at: $DB_PATH"
                            return
                            ;;
                        [Nn]* )
                            echo "📝 Please remember to update your parameters.yaml with the $TOOL_NAME database path later!"
                            return
                            ;;
                        * )
                            echo "⚠️ Invalid response. Please enter y or n."
                            ;;
                    esac
                done
                ;;
            * )
                echo "⚠️ Invalid input. Please enter y or n."
                ;;
        esac
    done
}

# --- Initialize setup ---

show_welcome

# Set work_dir
MODULE_WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_PATH=$PWD
read -p "Enter the working directory (Press Enter for default: $DEFAULT_PATH): " USER_WORK_DIR
SR_TAXONOMY_WORK_DIR="$(realpath "${USER_WORK_DIR:-$PWD}")"
echo "Working directory set to: $SR_TAXONOMY_WORK_DIR"
#echo "export ${SR_TAXONOMY_WORK_DIR} >> ~/.bashrc"

# --- Install conda environments ---

# Install conda envs: bbmap, dataviz, metaphlan, bracken
cd $DEFAULT_PATH
DEFAULT_CONDA_ENV_DIR=$(conda info --base)/envs

# Find or install...

# ...module environment
find_install_camp_env

# ...auxiliary environments
MODULE_PKGS=('bbmap' 'metaphlan' 'kraken2' 'bracken') # Add any additional conda packages here
for m in "${MODULE_PKGS[@]}"; do
    find_install_conda_env "$m"
done

# Download databses
declare -A DATABASE_PATHS

# === Example calls ===
ask_taxonomy_db "MetaPhlAn" "METAPHLAN_DB"
ask_taxonomy_db "Kraken2" "KRAKEN2_DB"

# Generate parameters.yaml
SCRIPT_DIR=$(pwd)
EXT_PATH="$DEFAULT_PATH/workflow/ext"
PARAMS_FILE="$MODULE_WORK_DIR/test_data/parameters.yaml" 
MPHLAN_PATH="${DATABASE_PATHS["METAPHLAN_DB"]}"
KRAKEN_PATH="${DATABASE_PATHS["KRAKEN2_DB"]}"
KRAKEN_EXECUTABLE=$(conda run -n bracken which kraken2 2>/dev/null)
BBMASK_SCR=$(conda run -n bbmap which bbmask.sh 2> /dev/null)
read -p "📏 How long are your reads?: " READ_LEN
read -p "📊 What is the minimum relative abundance you're considering? (Press Enter for default: 0.001): " MIN_REL_ABUND
MIN_REL_ABUND="${MIN_REL_ABUND:-0.001}"

# Remove existing parameters.yaml if present
[ -f "$PARAMS_FILE" ] && rm "$PARAMS_FILE"
# Create new parameters.yaml file
cat <<EOF > "$PARAMS_FILE"

#'''Parameters config.'''

# --- general --- #

ext: '$EXT_PATH'
conda_prefix: '$DEFAULT_CONDA_ENV_DIR'
mask: False
metaphlan: True
kraken2: True

min_rel_abund: $MIN_REL_ABUND


# --- masking --- #

bbmask_script: '$BBMASK_SCR'


# --- metaphlan --- #

metaphlan_database: '$MPHLAN_PATH'


# --- kraken2/bracken --- #

kraken_bracken_database: '$KRAKEN_PATH'
kraken2_executable: '$KRAKEN_EXECUTABLE'
read_len: $READ_LEN
EOF

echo "✅ parameters.yaml file created successfully in test_data/"

PARAMS_FILE="configs/parameters.yaml"

# Remove existing parameters.yaml if present
[ -f "$PARAMS_FILE" ] && rm "$PARAMS_FILE"
# Create new parameters.yaml file
cat <<EOF > "$PARAMS_FILE"
#'''Parameters config.'''

# --- general --- #

ext: '$EXT_PATH'
conda_prefix: '$DEFAULT_CONDA_ENV_DIR'
mask: False
metaphlan: True
kraken2: True

min_rel_abund: $MIN_REL_ABUND


# --- masking --- #

bbmask_script: '$BBMASK_SCR'


# --- metaphlan --- #

metaphlan_database: '$MPHLAN_PATH'


# --- kraken2/bracken --- #

kraken_bracken_database: '$KRAKEN_PATH'
kraken2_executable: '$KRAKEN_EXECUTABLE'
read_len: $READ_LEN
EOF

echo "✅ parameters.yaml file created successfully in configs/"

# Modify test_data/samples.csv
sed -i.bak "s|/path/to/camp_short-read-taxonomy|$MODULE_WORK_DIR|g" test_data/samples.csv

echo "✅ samples.csv successfully created in test_data/"

echo "🎯 Setup complete! You can now test the workflow using \`python workflow/short-read-taxonomy.py test\`"

