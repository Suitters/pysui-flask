#!/bin/bash
# Copyright (c) Frank V. Castellucci
# License: Apache-2.0


base_dir=${PWD##*/}
if test "$base_dir" = "pysui-flask";
then
    echo "Removing previous build artifacts... if any!"
    rm -rf "build"
    rm -rf "dist"
    rm -rf "pysui-flask.egg-info"
    echo "Building pysui-flask....."
    python3 -m build . --wheel
    tout=$(twine check "dist/*")
    if echo $tout | grep -q "PASSED"; then
            echo "Build successful!"
            exit 0
        else
            echo "Bad Build. Fix errors and rerun"
            exit -1
    fi
else
    echo "Command must run from pysui-flask folder."
fi
