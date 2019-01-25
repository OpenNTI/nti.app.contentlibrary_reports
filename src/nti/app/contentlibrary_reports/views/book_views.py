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

from nti.app.contentlibrary.interfaces import IResourceUsageStats

from nti.app.contentlibrary_reports import MessageFactory as _

from nti.app.contentlibrary_reports import VIEW_BOOK_PROGRESS_REPORT

from nti.app.contentlibrary_reports.views.view_mixins import AbstractBookReportView

from nti.app.contentlibrary_reports.content_metrics import ContentUnitMetrics

from nti.contentlibrary.interfaces import IContentPackageBundle

from nti.dataserver.users import User


logger = __import__('logging').getLogger(__name__)


_UserBookProgressStat = \
    namedtuple('UserBookProgressStat',
               ('userinfo', 'total_view_time', 'last_accessed'))


@view_config(context=IContentPackageBundle,
             name=VIEW_BOOK_PROGRESS_REPORT)
class BookProgressReportPdf(AbstractBookReportView):

    report_title = _(u'Progress Overview Report')

    # 15 minute floor; this will probably need to be site driven
    VIEW_TIME_MINUTE_FLOOR = 15

    def _get_last_view_time(self, user_stats):
        last_view_time = ''
        if user_stats.last_view_time:
            last_view_time = self._adjust_date(user_stats.last_view_time)
            last_view_time = self._format_datetime(last_view_time)
        return last_view_time

    def _get_total_view_time(self, user_stats):
        result = ''
        total_view_time = user_stats.total_view_time
        if total_view_time:
            in_minutes = total_view_time / 60
            in_base = floor(in_minutes / self.VIEW_TIME_MINUTE_FLOOR)
            result = int(in_base * self.VIEW_TIME_MINUTE_FLOOR)
        return str(result)

    def _get_book_estimated_access_time(self):
        ntiid = self.book.ContentPackages[0].ntiid
        metrics = ContentUnitMetrics(self.context)
        total_minutes = metrics.get_total_minutes(ntiid)
        return total_minutes

    def __call__(self):
        self._check_access()
        options = self.options
        book_stats = IResourceUsageStats(self.book, None)
        estimated_access_time = self._get_book_estimated_access_time()
        if book_stats is not None:
            usernames = book_stats.get_usernames_with_stats()
            user_infos = list()
            for username in usernames:
                user = User.get_user(username)
                user_infos.append(self.build_user_info(user))
            user_infos = sorted(user_infos)
            user_data = list()
            for user_info in user_infos:
                user_stats = book_stats.get_stats_for_user(user_info.username)
                last_view_time = self._get_last_view_time(user_stats)
                total_view_time = self._get_total_view_time(user_stats)
                # Now we may have a user that we floor to 0 minutes of view
                # time, which would make them equal to users who never viewed
                # the material and who do not end up in this report (our user
                # population is driven from view stats). Should we exclude
                # these users too?
                total_view_over_estimated_time = u'{}/{}'.format(total_view_time, estimated_access_time)
                user_result = _UserBookProgressStat(user_info,
                                                    total_view_over_estimated_time,
                                                    last_view_time)
                user_data.append(user_result)
            options['user_data'] = user_data
        return options
