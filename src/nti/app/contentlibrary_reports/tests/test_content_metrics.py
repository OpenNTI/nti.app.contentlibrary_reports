#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import assert_that

import unittest

from nti.app.contentlibrary_reports.content_metrics import ContentUnitMetrics
from nti.app.contentlibrary_reports.interfaces import IContentUnitMetrics
from nti.testing.matchers import verifiably_provides


class TestContentUnitMetrics(unittest.TestCase):

    def test_content_unit_metrics(self):
        cmetrics = ContentUnitMetrics(None)
        assert_that(cmetrics, verifiably_provides(IContentUnitMetrics))
