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

from zope import component

from pyramid.view import view_config

from nti.app.contentlibrary.interfaces import IResourceUsageStats

from nti.app.contentlibrary_reports import MessageFactory as _

from nti.app.contentlibrary_reports import VIEW_BOOK_CONCEPT_REPORT
from nti.app.contentlibrary_reports import VIEW_BOOK_PROGRESS_REPORT

from nti.app.contentlibrary_reports.views.view_mixins import AbstractBookReportView

from nti.app.contentlibrary_reports.interfaces import IContentUnitMetrics

from nti.app.contentlibrary_reports.content_metrics import ContentConsumptionTime

from nti.contentlibrary.interfaces import IContentPackageBundle

from nti.dataserver.users import User

from nti.app.contentlibrary_reports.interfaces import IConcepts

from nti.app.contentlibrary_reports.concepts import ConceptsEstimatedReadingTime


logger = __import__('logging').getLogger(__name__)


_UserBookProgressStat = \
    namedtuple('UserBookProgressStat',
               ('userinfo', 'total_view_time', 'last_accessed', 'is_complete'))


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
        result = 0
        total_view_time = user_stats.total_view_time
        if total_view_time:
            in_minutes = total_view_time / 60
            in_base = floor(in_minutes / self.VIEW_TIME_MINUTE_FLOOR)
            result = int(in_base * self.VIEW_TIME_MINUTE_FLOOR)
        return result

    def _get_book_estimated_access_time(self, values):
        """
        Return the expected consumption time, in minutes for
        the given ntiid.
        """
        ntiid = self.book.ContentPackages[0].ntiid
        cumetrics = component.getUtility(IContentUnitMetrics)
        metrics = cumetrics.process(self.context)
        expected_consumption_time = metrics[ntiid].get('expected_consumption_time')
        if expected_consumption_time is None:
            # No override, gather our metric.
            ctime = ContentConsumptionTime(metrics, values)
            expected_consumption_time = ctime.get_normalize_estimated_time_in_minutes(ntiid)
        return expected_consumption_time

    def __call__(self):
        self._check_access()
        values = self.readInput()
        options = self.options
        book_stats = IResourceUsageStats(self.book, None)
        estimated_consumption_time = self._get_book_estimated_access_time(values)
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
                is_complete = total_view_time \
                    and estimated_consumption_time \
                    and total_view_time >= estimated_consumption_time
                user_result = _UserBookProgressStat(user_info,
                                                    total_view_time,
                                                    last_view_time,
                                                    is_complete)
                user_data.append(user_result)
            options['user_data'] = user_data
            options['estimated_consumption_time'] = estimated_consumption_time
        return options


@view_config(context=IContentPackageBundle,
             name=VIEW_BOOK_CONCEPT_REPORT)
class BookConceptReportPdf(BookProgressReportPdf):
    """
    Extending our book progress report. This report will want to
    get user progress on each `concept` contained within this book.
    This book must have concepts defined (e.g. concepts.json) or we
    have nothing to do.

    Options should have:

    <concept_data> = {concept_name, concept_estimated_time, user_data}
    """

    report_title = _(u'Concept Progress Report')

    def _get_concept_estimated_access_time(self, values, concepts):
        cumetrics = component.getUtility(IContentUnitMetrics)
        metrics = cumetrics.process(self.context)
        cmtime = ContentConsumptionTime(metrics, values)
        certime = ConceptsEstimatedReadingTime(concepts, cmtime)
        concepts_metrics = certime.process()
        return concepts_metrics

    def _get_concept_tree_usage(self, concepts, ntiid_stats_map):
        if 'concepthierarchy' not in self.concepts:
            return None
        tree = self.concept_hierachy['concepthierarchy']
        concepts_usage = {}
        if 'concepts' in tree:
            concepts = tree['concepts']
            for concept_ntiid, concept in concepts.items():
                self._process_concept_tree(ntiid_stats_map, concept_ntiid, concept, concepts_usage)
        return concepts_usage

    def _process_concept_tree(self, ntiid_stats_map, concept_ntiid, concept, concepts_usage):
        cusage = {}
        cusage['name'] = cusage['name']
        usages = self._get_users_concept_usage(concept['contentunitntiids'], ntiid_stats_map)
        cusage['usages'] = usages
        concepts_usage[concept_ntiid] = cusage
        if 'concepts' in concept:
            subconcepts = concept['concepts']
            for subconcept_ntiid, subconcept in subconcepts.items():
                self._process_concept_tree(ntiid_stats_map, subconcept_ntiid, subconcept, concepts_usage)
                self._aggregate_concept_usage(concept_ntiid, subconcept_ntiid, concepts_usage)

    def _get_users_concept_usage(self, content_unit_ntiids, ntiid_stats_map):
        """
        @type  content_unit_ntiids: list
        @param content_unit_ntiids: list of content unit ntiids of a concept
        @type  ntiid_stats_map    : dictionary
        @param ntiid_stats_map    :
        @rtype : dictionary
        @return: total time spent on a concept by user
        """
        user_concept_stats = {}
        for unit_ntiid in content_unit_ntiids:
            if unit_ntiid in ntiid_stats_map:
                user_stats = ntiid_stats_map[unit_ntiid].user_stats
                for s_user in user_stats:
                    total_view_time = self._get_total_view_time(user_stats)
                    if s_user in user_concept_stats:
                        user_concept_stats[s_user] += total_view_time
                    else:
                        user_concept_stats[s_user] = total_view_time
        return user_concept_stats

    def _get_total_view_time(self, user_stats):
        result = 0
        total_view_time = user_stats.total_view_time
        if total_view_time:
            in_minutes = total_view_time / 60
            in_base = floor(in_minutes / self.VIEW_TIME_MINUTE_FLOOR)
            result = int(in_base * self.VIEW_TIME_MINUTE_FLOOR)
        return result

    def _aggregate_concept_usage(self, cparent_ntiid, cchild_ntiid, concepts_usage):
        """
        This method aggregate users usage from sub/child concept to parent concept
        """
        for user in concepts_usage[cchild_ntiid]['usages']:
            if user not in concepts_usage[cparent_ntiid]['usages']:
                concepts_usage[cparent_ntiid]['usages'][user] = concepts_usage[cchild_ntiid]['usages'][user]
            else:
                concepts_usage[cparent_ntiid]['usages'][user] += concepts_usage[cchild_ntiid]['usages'][user]

    def __call__(self):
        self._check_access()
        values = self.readInput()
        options = self.options
        book_stats = IResourceUsageStats(self.book, None)
        accum = book_stats.accum
        ntiid_stats_map = accum.ntiid_stats_map

        concepts = component.getUtility(IConcepts)
        concepts_metrics = self._get_concept_estimated_access_time(values, concepts)

        if book_stats is not None and concepts:
            concepts_usage = self._get_concept_tree_usage(concepts, ntiid_stats_map)
            #usernames = book_stats.get_usernames_with_stats()
            # TODO map concepts_usage with all book users
        return options
