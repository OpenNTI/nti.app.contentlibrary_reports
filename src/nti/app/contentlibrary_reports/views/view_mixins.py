#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from datetime import datetime

from pyramid.httpexceptions import HTTPForbidden

from zope.cachedescriptors.property import Lazy

from nti.app.contentlibrary_reports.interfaces import ACT_VIEW_BOOK_REPORTS

from nti.app.contenttypes.reports.views.view_mixins import AbstractReportView

from nti.appserver.pyramid_authorization import has_permission

logger = __import__('logging').getLogger(__name__)

MAX_FILENAME_LEN = 255  # 255 char max length (OSX (APFS) and Win10 (NTFS))

class AbstractBookReportView(AbstractReportView):
    """
    An abstract report view that can be used on something that can be adapted
    to an :class:`IContentPackageBundle`.
    """

    def _check_access(self):
        if not has_permission(ACT_VIEW_BOOK_REPORTS, self.book, self.request):
            raise HTTPForbidden()

    @property
    def filename(self):
        # Format: <prefix>_<title>.pdf
        # Prefix gets any portion not taken by _<title>.pdf
        prefix = self.book_name() and self.book_name()[:self._max_prefix_length]
        basename = self.report_title if not prefix else u'{0}_{1}'.format(prefix, self.report_title)
        return u'{0}.pdf'.format(basename[:self._max_title_length])

    @property
    def _max_prefix_length(self):
        # MAX less room for "_<title>.pdf"
        return max(MAX_FILENAME_LEN - (len(self.report_title) + 5), 0)

    @property
    def _max_title_length(self):
        # MAX less room for ".pdf"
        return MAX_FILENAME_LEN - 4

    @Lazy
    def book(self):
        return self.context

    def book_name(self):
        return self.book.title

    def generate_footer(self):
        date = self._adjust_date(datetime.utcnow())
        date = date.strftime('%b %d, %Y %I:%M %p')
        title = self.report_title
        book_name = self.book_name()
        return "%s %s %s %s" % (title, book_name, date, self.timezone_info_str)

    def readInput(self, value=None):
        if self.request.body:
            values = super(AbstractBookReportView, self).readInput(value)
        else:
            values = dict(self.request.params)
        return values
