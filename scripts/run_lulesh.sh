#!/bin/bash

if [ -z "$1" ]; then
    echo "Please provide a spec file path"
    exit 1
fi

SPEC="$1"

maestro run -y "$SPEC"

CONDUCT_PID=$(pgrep "conductor")
if [ -z "$CONDUCT_PID" ]; then
    echo "Failed to find conductor"
    exit 1
fi

wait $CONDUCTOR_PID || exit "Conductor failed"

exit 0
