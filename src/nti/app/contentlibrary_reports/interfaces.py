#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.security.permission import Permission

ACT_VIEW_BOOK_REPORTS = Permission('nti.actions.contentlibrary_reports.view_reports')


class IContentUnitMetrics(interface.Interface):
    """
    An interface for utility to get content_metrics.json from content package
    """
