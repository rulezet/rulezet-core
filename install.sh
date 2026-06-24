#!/bin/bash

# Couleurs
GREEN="\033[0;32m"
CYAN="\033[0;36m"
RESET="\033[0m"

echo -e "${CYAN}🚀 Starting the installation process...${RESET}"

sudo apt install -y python3.12-venv
python3 -m venv env
. env/bin/activate

echo -e "${CYAN}📦 Install the Python dependencies...${RESET}"
pip install -r requirements.txt

echo -e "${CYAN}🐘 Install PostgreSQL ...${RESET}"
./install_postgresql.sh

chmod +x ./launch.sh

# Init required git submodules
echo -e "${CYAN}📂 Initialising git submodules...${RESET}"
git submodule update --init --recursive --depth 1 app/modules/rulezet-cast
git submodule update --init --recursive --depth 1 app/modules/pivotick

# CTI submodule (mitre/cti) — large repo, only initialise if not already present
if [ ! -f "app/modules/cti/enterprise-attack/enterprise-attack.json" ]; then
    echo -e "${CYAN}🛡️  Cloning MITRE ATT&CK CTI data (shallow, may take a moment)...${RESET}"
    git submodule update --init --depth 1 app/modules/cti
else
    echo -e "${GREEN}✔ MITRE CTI submodule already present.${RESET}"
fi

. env/bin/activate

echo -e "${GREEN}🎮 Launch the application...${RESET}"
./launch.sh -i
