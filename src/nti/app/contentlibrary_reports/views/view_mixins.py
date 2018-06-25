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

from zope.security.management import checkPermission

from nti.app.contentlibrary_reports.interfaces import ACT_VIEW_BOOK_REPORTS

from nti.app.contenttypes.reports.views.view_mixins import AbstractReportView

from nti.dataserver.authorization import is_admin_or_site_admin

logger = __import__('logging').getLogger(__name__)


class AbstractBookReportView(AbstractReportView):
    """
    An abstract report view that can be used on something that can be adapted
    to an :class:`IContentPackageBundle`.
    """

    def _check_access(self):
        if is_admin_or_site_admin(self.remoteUser):
            return True

        if not checkPermission(ACT_VIEW_BOOK_REPORTS.id, self.book):
            raise HTTPForbidden()

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
