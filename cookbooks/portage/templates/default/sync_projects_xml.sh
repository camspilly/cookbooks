#!/bin/bash

repository_name="${1}"
repository_path="${3}"

[[ ${repository_name} == "<%= node[:portage][:repo] %>" ]] || exit 0

source /lib/gentoo/functions.sh

ebegin "Updating projects.xml"
wget -q -P "${repository_path}"/metadata/ -N https://api.gentoo.org/metastructure/projects.xml
eend $?
