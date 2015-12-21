 #!/bin/sh
#
# Patchwork - automated patch tracking system
# Copyright (C) 2008 Jeremy Kerr <jk@ozlabs.org>
#
# This file is part of the Patchwork package.
#
# Patchwork is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Patchwork is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Patchwork; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


ADDRESS=0.0.0.0:8000
CFG=patchwork.settings.dev-sqlite

# . /sources/intel/patchwork/venv/bin/activate

export DJANGO_SETTINGS_MODULE=$CFG

PATCHWORK_BASE=`readlink -e /sources/intel/patchwork/`

logger "Starting patchwork email script"
logger $@
echo "$@"

PYTHONPATH="$PATCHWORK_BASE":"$PATCHWORK_BASE/lib/python:$PYTHONPATH" \
        DJANGO_SETTINGS_MODULE=patchwork.settings.dev-sqlite \
        "$PATCHWORK_BASE/patchwork/bin/parsemail.py" --verbosity=debug $@

# deactivate

exit 0
