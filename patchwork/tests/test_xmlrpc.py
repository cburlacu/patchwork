# Patchwork - automated patch tracking system
# Copyright (C) 2014 Jeremy Kerr <jk@ozlabs.org>
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

import unittest
import urlparse

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import LiveServerTestCase
from django.utils.six.moves import xmlrpc_client

from patchwork.models import Patch, State, EventLog
from patchwork.tests.test_user import TestUser
from patchwork.tests.utils import defaults, TestSeries


@unittest.skipUnless(settings.ENABLE_XMLRPC,
                     'requires xmlrpc interface (use the ENABLE_XMLRPC '
                     'setting)')
class XMLRPCTest(LiveServerTestCase):
    fixtures = ['default_states', 'default_events']

    def _insert_patch(self):
        patch = Patch(project=defaults.project,
                      submitter=defaults.patch_author_person,
                      msgid=defaults.patch_name,
                      content=defaults.patch)
        patch.save()
        return patch

    def setUp(self):
        defaults.project.save()
        defaults.patch_author_person.save()
        self.maintainer = TestUser(username='maintainer')
        self.maintainer.add_to_maintainers(defaults.project)

        p = urlparse.urlparse(self.live_server_url)
        self.url = (p.scheme + '://' + self.maintainer.username + ':' +
                    self.maintainer.password + '@' + p.netloc + p.path +
                    reverse('patchwork.views.xmlrpc.xmlrpc'))
        self.rpc = xmlrpc_client.Server(self.url)

    def testGetRedirect(self):
        response = self.client.patch(self.url)
        self.assertRedirects(response,
                             reverse('patchwork.views.help',
                                     kwargs={'path': 'pwclient/'}))

    def testList(self):
        patch = self._insert_patch()

        patches = self.rpc.patch_list()
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0]['id'], patch.id)

    def testSetPatchState(self):
        series = TestSeries(1, has_cover_letter=False)
        series.insert()
        patch = Patch.objects.all()[0]

        superseded = State.objects.get(name='Superseded')
        self.rpc.patch_set(patch.pk, {'state': superseded.pk})
        patch = Patch.objects.get(pk=patch.pk)
        self.assertEqual(patch.state, superseded)

        # make sure we've logged the correct user with the change event
        self.assertEqual(Patch.objects.count(), 1)
        events = EventLog.objects.filter(event_id=2)
        self.assertEqual(events.count(), 1)
        event = events[0]
        self.assertEquals(event.user, self.maintainer.user)
