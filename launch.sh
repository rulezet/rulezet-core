#!/bin/bash

# The rule editor and the rule tester are submodules installed editable (pyproject.toml, uv):
# fetch / install them when this checkout predates them. Run inside the virtualenv (.venv/).
function ensure_editor {
    for mod in rulezet-editor rulezet-tester; do
        if [ ! -f app/modules/$mod/pyproject.toml ]; then
            git submodule update --init --recursive app/modules/$mod
        fi
        python3 -c "import ${mod//-/_}" 2>/dev/null || uv pip install --python "$(command -v python3)" -e ./app/modules/$mod
    done
}

function launch {
    ensure_editor
    export FLASKENV="development"
    python3 app.py
}

function test {
    export FLASKENV="testing"
    pytest tests
}

function init_db {
	python3 app.py -i
}

function reload_db {
	python3 app.py -r
}

function delete_db {
    python3 app.py -d
}


if [ "$1" ]; then
    case $1 in
        -l | --launch )             launch;
                                        ;;
		-i | --init_db )            init_db;
                                        ;;
		-r | --reload_db )          reload_db;
                                        ;;
        -d | --delete_db )          delete_db;
                                        ;;
        -t | --test )               test;
                                        ;;
    esac
    exit $?
else
	launch
fi
