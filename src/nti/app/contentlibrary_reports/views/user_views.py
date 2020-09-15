#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from collections import namedtuple

from pyramid import httpexceptions as hexc

from pyramid.config import not_

from pyramid.httpexceptions import HTTPForbidden

from pyramid.view import view_config

from zope import component

from zope.cachedescriptors.property import Lazy

from nti.app.contentlibrary.interfaces import IUserBundleRecord
from nti.app.contentlibrary.interfaces import IResourceUsageStats

from nti.app.contentlibrary_reports import VIEW_USER_BOOK_PROGRESS_REPORT

from nti.app.contentlibrary_reports import MessageFactory as _

from nti.app.contentlibrary_reports.views.view_mixins import ReportCSVMixin
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


@view_config(route_name='objects.generic.traversal',
             context=IUserBundleRecord,
             name=VIEW_USER_BOOK_PROGRESS_REPORT,
             accept='application/pdf',
             request_param=not_('format'))
@view_config(route_name='objects.generic.traversal',
             context=IUserBundleRecord,
             name=VIEW_USER_BOOK_PROGRESS_REPORT,
             request_param='format=application/pdf')
class UserBookProgressReportPdf(AbstractBookReportView):
    """
    For a given bundle (assume one package? iterate through
    packages [probably]), the units under a package (chapters)
    will display metrics for a user.
    """

    report_title = _(u'User Progress Report')

    #: 15 minute floor; this will probably need to be site driven
    VIEW_TIME_MINUTE_FLOOR = 15

    @property
    def _user_filename_part(self):
        user_info = self.build_user_info(self.user)
        return self.user_as_affix(self.user, user_info=user_info)

    @property
    def filename(self):
        user_prefix = self._user_filename_part
        book_part = super(UserBookProgressReportPdf, self).filename
        return self._build_filename([user_prefix, book_part], extension='')

    @property
    def _max_title_length(self):
        # Max - the username part
        result = super(UserBookProgressReportPdf, self)._max_title_length
        return result - len(self._user_filename_part)

    def _can_admin_user(self, user):
        # Verify a site admin is administering a user in their site.
        result = True
        if is_site_admin(self.remoteUser):
            admin_utility = component.getUtility(ISiteAdminUtility)
            result = admin_utility.can_administer_user(self.remoteUser, user)
        return result

    def _check_access(self):
        super(UserBookProgressReportPdf, self)._check_access()
        if not self._can_admin_user(self.user):
            raise HTTPForbidden()

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
                    section_last_view_time = getattr(content_stats, 'last_view_time', 0)
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

    def _get_stats(self):
        cmetrics = component.getUtility(IContentUnitMetrics)
        metrics = cmetrics.process(self.book)
        if metrics is None:
            raise hexc.HTTPNotFound()

        values = self.readInput()
        book_stats = component.queryMultiAdapter((self.book, self.user),
                                                 IResourceUsageStats)

        cmtime = ContentConsumptionTime(metrics, values)
        chapter_data = list()
        try:
            # XXX: First package
            package = self.book.ContentPackages[0]
        except IndexError:
            package = None
        if book_stats is not None and package is not None:
            stat_map = {x.ntiid: x for x in book_stats.get_stats()}
            for content_unit in package.children or ():
                chapter_progress_stat = self._get_chapter_stats(content_unit, stat_map, cmtime)
                chapter_data.append(chapter_progress_stat)
        return chapter_data

    def _do_call(self):
        options = self.options
        options['user'] = self.build_user_info(self.user)
        chapter_stats = self._get_stats()
        if chapter_stats:
            aggregate_complete_count = 0
            aggregate_content_unit_count = 0
            last_accessed = None
            for chapter_progress_stat in chapter_stats or ():
                aggregate_complete_count += chapter_progress_stat.complete_content_count
                aggregate_content_unit_count += chapter_progress_stat.content_unit_count
                if last_accessed is None:
                    last_accessed = chapter_progress_stat.last_view_time_date
                elif chapter_progress_stat.last_view_time_date:
                    last_accessed = max(last_accessed,
                                        chapter_progress_stat.last_view_time_date)
            options['chapter_data'] = chapter_stats
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

    def __call__(self):
        self._check_access()
        return self._do_call()


@view_config(route_name='objects.generic.traversal',
             context=IUserBundleRecord,
             name=VIEW_USER_BOOK_PROGRESS_REPORT,
             accept='text/csv',
             request_param=not_('format'))
@view_config(route_name='objects.generic.traversal',
             context=IUserBundleRecord,
             name=VIEW_USER_BOOK_PROGRESS_REPORT,
             request_param='format=text/csv')
class UserBookProgressReportCSV(UserBookProgressReportPdf, ReportCSVMixin):

    @Lazy
    def header_field_map(self):
        return {
            'Title': 'title',
            'Topics Completed': 'topics_completed',
            'Topic Count': 'topic_count',
            'Progress (min)': 'progress_min',
            'Progress Required (min)': 'progress_required_min',
            'Last Accessed': 'last_accessed'
        }

    @Lazy
    def header_row(self):
        return ('Title', 'Topics Completed', 'Topic Count',
                'Progress (min)', 'Progress Required (min)', 'Last Accessed')

    @Lazy
    def show_supplemental_info(self):
        return False


    def _get_report_data(self):
        chapter_stats = self._get_stats()
        result = []
        # Map this into our header dict
        # total_view_time is in min
        for chapter_stat in chapter_stats or ():
            if chapter_stat.has_expected_consumption:
                result.append({'title': chapter_stat.title,
                               'topics_completed': chapter_stat.complete_content_count,
                               'topic_count': chapter_stat.content_unit_count,
                               'progress_min': chapter_stat.total_view_time,
                               'progress_required_min': chapter_stat.chapter_consumption_time,
                               'last_accessed': chapter_stat.last_accessed})
            else:
                result.append({'title': chapter_stat.title,
                               'topics_completed': '',
                               'topic_count': '',
                               'progress_min': '',
                               'progress_required_min': '',
                               'last_accessed': ''})
        return result

    @property
    def filename(self):
        user_prefix = self._user_filename_part
        book_part = super(UserBookProgressReportPdf, self).filename
        return self._build_filename([user_prefix, book_part], extension='csv')

    def _do_call(self):
        return self._do_create_response(filename=self.filename)
