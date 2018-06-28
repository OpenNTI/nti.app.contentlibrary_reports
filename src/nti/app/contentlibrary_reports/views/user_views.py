#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from collections import namedtuple

from math import floor

from pyramid.view import view_config

from zope import component

from zope.cachedescriptors.property import Lazy

from nti.app.contentlibrary.interfaces import IUserBundleRecord
from nti.app.contentlibrary.interfaces import IResourceUsageStats

from nti.app.contentlibrary_reports import VIEW_USER_BOOK_PROGRESS_REPORT

from nti.app.contentlibrary_reports import MessageFactory as _

from nti.app.contentlibrary_reports.views.view_mixins import AbstractBookReportView

from nti.dataserver.authorization import is_site_admin

from nti.dataserver.interfaces import ISiteAdminUtility

logger = __import__('logging').getLogger(__name__)


_UserBookProgressStat = \
    namedtuple('UserBookProgressStat',
               ('title', 'content_unit_count', 'content_data_count',
                'total_view_time', 'last_accessed'))

@view_config(context=IUserBundleRecord,
             name=VIEW_USER_BOOK_PROGRESS_REPORT)
class UserBookProgressReportPdf(AbstractBookReportView):
    """
    For a given bundle (assume one package? iterate through
    packages [probably]), the units under a package (chapters)
    will display metrics for a user.
    """

    report_title = _(u'User Progress Report')

    # 15 minute floor; this will probably need to be site driven
    VIEW_TIME_MINUTE_FLOOR = 15

    def _can_admin_user(self, user):
        # Verify a site admin is administering a user in their site.
        result = True
        if is_site_admin(self.remoteUser):
            admin_utility = component.getUtility(ISiteAdminUtility)
            result = admin_utility.can_administer_user(self.remoteUser, user)
        return result

    def _check_access(self):
        super(UserBookProgressReportPdf, self)._check_access()
        self._can_admin_user(self.user)

    @Lazy
    def user(self):
        return self.context.User

    @Lazy
    def book(self):
        return self.context.Bundle

    def _get_last_view_time(self, last_view_time):
        if last_view_time:
            last_view_time = self._adjust_date(last_view_time)
            last_view_time = self._format_datetime(last_view_time)
        return last_view_time

    def _get_total_view_time(self, total_view_time):
        if total_view_time:
            in_minutes = total_view_time / 60
            in_base = floor(in_minutes / self.VIEW_TIME_MINUTE_FLOOR)
            result = int(in_base * self.VIEW_TIME_MINUTE_FLOOR)
        return str(result)

    def _get_chapter_stats(self, chapter_unit, stat_map):
        total_view_time = 0
        last_view_time = None
        content_count = 0
        content_data_count = 0
        for content_unit in chapter_unit.children or ():
            # TODO: Should we go recursive here (probably)?
            content_count += 1
            content_stats = stat_map.get(content_unit.ntiid)
            if content_stats and content_stats.total_view_time:
                content_data_count += 1
                total_view_time += content_stats.total_view_time
                if content_stats.last_view_time:
                    if last_view_time is None:
                        last_view_time = content_stats.last_view_time
                    else:
                        last_view_time = max(last_view_time,
                                             content_stats.last_view_time)
        last_view_time = self._get_last_view_time(last_view_time)
        total_view_time = self._get_total_view_time(total_view_time)
        return _UserBookProgressStat(chapter_unit.title,
                                     content_count,
                                     content_data_count,
                                     total_view_time,
                                     last_view_time)

    def __call__(self):
        self._check_access()
        options = self.options
        options['user_info'] = self.build_user_info(self.user)
        book_stats = component.queryMultiAdapter((self.book, self.user),
                                                 IResourceUsageStats)
        try:
            # XXX: First package
            package = self.book.ContentPackages[0]
        except IndexError:
            package = None
        if book_stats is not None and package is not None:
            stat_map = {x.ntiid:x for x in book_stats.get_stats()}
            chapter_data = list()
            for content_unit in package.children or ():
                chapter_progress_stat = self._get_chapter_stats(content_unit, stat_map)
                chapter_data.append(chapter_progress_stat)
            options['chapter_data'] = chapter_data
        return options
