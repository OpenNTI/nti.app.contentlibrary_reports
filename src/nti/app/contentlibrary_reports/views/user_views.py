#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from collections import namedtuple

from pyramid.view import view_config

from zope import component

from zope.cachedescriptors.property import Lazy

from nti.app.contentlibrary.interfaces import IUserBundleRecord
from nti.app.contentlibrary.interfaces import IResourceUsageStats

from nti.app.contentlibrary_reports import VIEW_USER_BOOK_PROGRESS_REPORT

from nti.app.contentlibrary_reports import MessageFactory as _

from nti.app.contentlibrary_reports.views.view_mixins import AbstractBookReportView

from nti.app.contenttypes.reports.views.table_utils import TableCell

from nti.dataserver.authorization import is_site_admin

from nti.dataserver.interfaces import ISiteAdminUtility

from nti.app.contentlibrary_reports.content_metrics import ContentConsumptionTime

from nti.app.contentlibrary_reports.interfaces import IContentUnitMetrics

logger = __import__('logging').getLogger(__name__)


_UserBookProgressStat = \
    namedtuple('UserBookProgressStat',
               ('title',
                'complete_content_count',
                'content_unit_count',
                'content_data_count',
                'total_view_time',
                'last_accessed',
                'last_view_time_date',
                'is_complete',
                'chapter_consumption_time',
                'has_expected_consumption'))


@view_config(context=IUserBundleRecord,
             name=VIEW_USER_BOOK_PROGRESS_REPORT)
class UserBookProgressReportPdf(AbstractBookReportView):
    """
    For a given bundle (assume one package? iterate through
    packages [probably]), the units under a package (chapters)
    will display metrics for a user.
    """

    report_title = _(u'User Progress Report')

    #: 15 minute floor; this will probably need to be site driven
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

    def _get_display_last_view_time(self, last_view_time):
        if last_view_time:
            last_view_time = self._adjust_date(last_view_time)
            last_view_time = self._format_datetime(last_view_time)
        return last_view_time

    def _get_total_view_time(self, total_view_time):
        result = ''
        if total_view_time:
            in_minutes = total_view_time / 60
            result = int(in_minutes)
        return str(result)

    def _get_children_view_time(self, parent_unit, stat_map):
        """
        Get the total view time (in minutes) for our given unit's children, recursively.
        """
        result = 0
        for child_unit in parent_unit.children or ():
            content_stats = stat_map.get(child_unit.ntiid)
            if content_stats and content_stats.total_view_time:
                result += content_stats.total_view_time
            result += self._get_children_view_time(child_unit, stat_map)
        return result

    def _get_chapter_stats(self, chapter_unit, stat_map, cmtime):
        """
        Gather a stat for the given chapter (content_unit). We will return analysis
        on whether the user spent enough time (is_complete) on the underlying sections
        for our given chapter.
        """
        total_view_time = 0
        last_view_time = None
        content_count = 0
        content_data_count = 0
        complete_content_count = 0

        # If this is 0, that means this chapter is not necessary for a user
        # completing the bundle material. The underling content counts will
        # not count towards the aggregate of the book. This means we will
        # not return access time for these chapters.
        chapter_consumption_time = self._get_expected_consumption_time(cmtime, chapter_unit.ntiid)

        if chapter_consumption_time:
            for content_unit in chapter_unit.children or ():
                content_count += 1
                section_view_time = 0
                content_stats = stat_map.get(content_unit.ntiid)
                section_view_time += getattr(content_stats, 'total_view_time', 0)
                section_view_time += self._get_children_view_time(content_unit, stat_map)
                if section_view_time:
                    content_data_count += 1
                    if section_view_time > self._get_expected_consumption_time(cmtime, content_unit.ntiid):
                        complete_content_count += 1
                    total_view_time += section_view_time
                    section_last_view_time = getattr(content_stats, 'last_view_time')
                    if section_last_view_time:
                        if last_view_time is None:
                            last_view_time = section_last_view_time
                        else:
                            last_view_time = max(last_view_time,
                                                 section_last_view_time)
        last_view_time_date = last_view_time
        last_view_time = self._get_display_last_view_time(last_view_time)
        total_view_time = self._get_total_view_time(total_view_time)
        is_complete = complete_content_count >= content_count
        has_expected_consumption = bool(chapter_consumption_time)

        return _UserBookProgressStat(chapter_unit.title,
                                     complete_content_count,
                                     content_count,
                                     content_data_count,
                                     total_view_time,
                                     last_view_time,
                                     last_view_time_date,
                                     is_complete,
                                     chapter_consumption_time,
                                     has_expected_consumption)

    def _get_expected_consumption_time(self, cmtime, ntiid):
        """
        Return the expected consumption time, in minutes for
        the given ntiid.
        """
        expected_consumption_time = cmtime.content_metrics[ntiid].get('expected_consumption_time')
        if expected_consumption_time is None:
            # No override
            expected_consumption_time = cmtime.get_normalize_estimated_time_in_minutes(ntiid)
        return expected_consumption_time

    def __call__(self):
        self._check_access()
        values = self.readInput()
        options = self.options
        options['user'] = self.build_user_info(self.user)
        book_stats = component.queryMultiAdapter((self.book, self.user),
                                                 IResourceUsageStats)
        cmetrics = component.getUtility(IContentUnitMetrics)
        metrics = cmetrics.process(self.book)
        cmtime = ContentConsumptionTime(metrics, values)
        try:
            # XXX: First package
            package = self.book.ContentPackages[0]
        except IndexError:
            package = None
        if book_stats is not None and package is not None:
            stat_map = {x.ntiid: x for x in book_stats.get_stats()}
            chapter_data = list()
            aggregate_complete_count = 0
            aggregate_content_unit_count = 0
            last_accessed = None
            for content_unit in package.children or ():
                chapter_progress_stat = self._get_chapter_stats(content_unit, stat_map, cmtime)
                chapter_data.append(chapter_progress_stat)
                aggregate_complete_count += chapter_progress_stat.complete_content_count
                aggregate_content_unit_count += chapter_progress_stat.content_unit_count
                if last_accessed is None:
                    last_accessed = chapter_progress_stat.last_view_time_date
                elif chapter_progress_stat.last_view_time_date:
                    last_accessed = max(last_accessed,
                                        chapter_progress_stat.last_view_time_date)
            options['chapter_data'] = chapter_data
            options['last_accessed'] = self._get_display_last_view_time(last_accessed)
            options['aggregate_complete_count'] = aggregate_complete_count
            options['aggregate_content_unit_count'] = aggregate_content_unit_count

        # Top right header_table data on the cover page.
        data = [ ('Name:', options['user'].display or ''),
                 ('Login:', options['user'].username or ''),
                 ('Book:', self.book_name() or ''),
                 (TableCell('Times in %s ' % self.timezone_displayname, colspan=2),'NTI_COLSPAN') ]

        header_options = self.get_top_header_options(data=data)
        options.update(header_options)
        return options
