#!/bin/bash

# The rule editor is a submodule installed editable (requirements.txt): fetch / install it
# when this checkout predates it.
function ensure_editor {
    if [ ! -f app/modules/rulezet-editor/pyproject.toml ]; then
        git submodule update --init --recursive app/modules/rulezet-editor
    fi
    python3 -c "import rulezet_editor" 2>/dev/null || pip install -e ./app/modules/rulezet-editor
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
