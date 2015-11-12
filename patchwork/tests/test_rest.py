# Patchwork - automated patch tracking system
# Copyright (C) 2015 Intel Corporation
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

from django.test import Client
import patchwork.tests.test_series as test_series
from patchwork.models import Series, Patch

import datetime
import hashlib
import json
import re

import dateutil.parser


entry_points = {
    '/': {
        'flags': (),
    },
    '/projects/': {
        'flags': ('is_list',),
    },
    '/projects/%(project_linkname)s/': {
        'flags': (),
    },
    '/projects/%(project_id)s/': {
        'flags': (),
    },
    '/projects/%(project_linkname)s/events/': {
        'flags': ('is_list',),
    },
    '/projects/%(project_id)s/events/': {
        'flags': ('is_list',),
    },
    '/projects/%(project_linkname)s/series/': {
        'flags': ('is_list',),
    },
    '/projects/%(project_id)s/series/': {
        'flags': ('is_list', ),
    },
    '/series/': {
        'flags': ('is_list',),
    },
    '/series/%(series_id)s/': {
        'flags': (),
    },
    '/series/%(series_id)s/revisions/': {
        'flags': ('is_list',),
    },
    '/series/%(series_id)s/revisions/%(version)s/': {
        'flags': (),
    },
    '/series/%(series_id)s/revisions/%(version)s/mbox/': {
        'flags': ('not_json',),
    },
    '/patches/': {
        'flags': ('is_list',),
    },
    '/patches/%(patch_id)s/': {
        'flags': (),
    },
    '/patches/%(patch_id)s/mbox/': {
        'flags': ('not_json',),
    },
}


class APITest(test_series.Series0010):

    def setUp(self):
        super(APITest, self).setUp()
        self.series = Series.objects.all()[0]
        self.patch = Patch.objects.all()[2]

    def check_mbox(self, api_url, filename, md5sum):
        response = self.client.get(api_url)
        s = re.search("filename=([\w\.\-_]+)",
                      response["Content-Disposition"]).group(1)
        self.assertEqual(s, filename)

        # With MySQL, primary keys keep growing and so the actual patch ids
        # will depend on the previous tests run. Make sure to canonicalize
        # the mbox file so we can compare md5sums
        content = re.sub('^X-Patchwork-Id: .*$', 'X-Patchwork-Id: 1',
                         response.content, flags=re.M)
        content_hash = hashlib.md5()
        content_hash.update(content)
        self.assertEqual(content_hash.hexdigest(), md5sum)

    def get(self, url, params={}):
        return self.client.get('/api/1.0' + url % {
                'project_id': self.project.pk,
                'project_linkname': self.project.linkname,
                'series_id': self.series.pk,
                'version': 1,
                'patch_id': self.patch.pk,
        }, params)

    def get_json(self, url, params={}):
        return json.loads(self.get(url, params).content)

    def testEntryPointPresence(self):
        for entry_point in entry_points:
            r = self.get(entry_point)
            self.assertEqual(r.status_code, 200)

    def testList(self):
        for entry_point in entry_points:
            meta = entry_points[entry_point]
            if 'not_json' in meta['flags']:
                continue

            json = self.get_json(entry_point)

            if 'is_list' not in meta['flags']:
                self.assertTrue('count' not in json)
                continue

            self.assertTrue('count' in json)
            self.assertTrue('next' in json)
            self.assertTrue('previous' in json)
            self.assertTrue('results' in json)

    def testRevisionPatchOrdering(self):
        revision = self.get_json('/series/%(series_id)s/revisions/1/')
        self.assertEqual(revision['version'], 1)
        patches = revision['patches']
        self.assertEqual(len(patches), 4)
        i = 1
        for patch_id in patches:
            patch = self.get_json('/patches/%d/' % patch_id)
            self.assertTrue('[%d/4]' % i in patch['name'])
            i += 1

    def testSeriesMbox(self):
        self.check_mbox("/api/1.0/series/%s/revisions/1/mbox/" % self.series.pk,
                        'for_each_-intel_-crtc-v2.mbox',
                        '42e2b2c9eeccf912c998be41683f50d7')

    def testPatchMbox(self):
        self.check_mbox("/api/1.0/patches/%s/mbox/" % self.patch.pk,
                        '3-4-drm-i915-Introduce-a-for_each_crtc-macro.patch',
                        'b951af09618c6360516f16ed97a30753')

    def testSeriesNewRevisionEvent(self):
        # no 'since' parameter
        events = self.get_json('/projects/%(project_id)s/events/')
        self.assertEqual(events['count'], 1)
        event = events['results'][0]
        self.assertEqual(event['parameters']['revision'], 1)

        event_time_str = event['event_time']
        event_time = dateutil.parser.parse(event_time_str)
        before = (event_time - datetime.timedelta(minutes=1)).isoformat()
        after = (event_time + datetime.timedelta(minutes=1)).isoformat()

        # strictly inferior timestamp, should return the event
        events = self.get_json('/projects/%(project_id)s/events/',
                               params={'since': before})
        self.assertEqual(events['count'], 1)
        event = events['results'][0]
        self.assertEqual(event['parameters']['revision'], 1)

        # same timestamp, should return no event
        events = self.get_json('/projects/%(project_id)s/events/',
                               params={'since': event_time_str})
        self.assertEqual(events['count'], 0)

        # strictly superior timestamp, should return no event
        events = self.get_json('/projects/%(project_id)s/events/',
                               params={'since': after})
        self.assertEqual(events['count'], 0)

    def testNumQueries(self):
        # using the related=expand parameter shouldn't make the number of
        # queries explode.
        with self.assertNumQueries(2):
            self.get('/projects/%(project_id)s/series/')
        with self.assertNumQueries(2):
            self.get('/projects/%(project_id)s/series/',
                     params={'related': 'expand'})
