#!/bin/sh

cd $(dirname "$0")

NAME="baconx.zip"

if [ -e "$NAME" ]
then
	rm "$NAME"
fi

zip -r "$NAME" "io_mesh_roomle"