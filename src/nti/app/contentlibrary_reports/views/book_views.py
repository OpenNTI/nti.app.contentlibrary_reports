#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import itertools

from collections import namedtuple

from math import floor

from pyramid.config import not_

from zope import component

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from zope.cachedescriptors.property import Lazy

from nti.app.contentlibrary.interfaces import IResourceUsageStats

from nti.app.contentlibrary_reports import MessageFactory as _

from nti.app.contentlibrary_reports import VIEW_BOOK_CONCEPT_REPORT
from nti.app.contentlibrary_reports import VIEW_BOOK_PROGRESS_REPORT

from nti.app.contentlibrary_reports.views.view_mixins import ReportCSVMixin
from nti.app.contentlibrary_reports.views.view_mixins import AbstractBookReportView

from nti.app.contentlibrary_reports.interfaces import IContentUnitMetrics

from nti.app.contentlibrary_reports.content_metrics import ContentConsumptionTime

from nti.contentlibrary.interfaces import IContentPackageBundle

from nti.dataserver.users import User

from nti.app.contentlibrary_reports.interfaces import IConcepts

from nti.app.contentlibrary_reports.concepts import ConceptsEstimatedReadingTime

from nti.ntiids.ntiids import find_object_with_ntiid


logger = __import__('logging').getLogger(__name__)


_UserBookProgressStat = \
    namedtuple('UserBookProgressStat',
               ('userinfo', 'total_view_time', 'last_accessed', 'is_complete'))


@view_config(route_name='objects.generic.traversal',
             context=IContentPackageBundle,
             name=VIEW_BOOK_PROGRESS_REPORT,
             accept='application/pdf',
             request_param=not_('format'))
@view_config(route_name='objects.generic.traversal',
             context=IContentPackageBundle,
             name=VIEW_BOOK_PROGRESS_REPORT,
             request_param='format=application/pdf')
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

    def _get_top_header_options(self):
        data = [(self.book_name(),),
                ('Times in %s ' % self.timezone_displayname,)]
        return super(BookProgressReportPdf,self).get_top_header_options(data, col_widths=[1])

    def _check_content_metrics(self):
        cumetrics = component.getUtility(IContentUnitMetrics)
        metrics = cumetrics.process(self.context)
        if metrics is None:
            raise hexc.HTTPNotFound()

    def _get_stats(self):
        """
        Return a tuple of user_data (_UserBookProgressStat objects) and
        estimated_consumption_time.
        """
        self._check_content_metrics()
        values = self.readInput()
        book_stats = IResourceUsageStats(self.book, None)
        estimated_consumption_time = self._get_book_estimated_access_time(values)
        user_data_list = list()
        if book_stats is not None:
            usernames = book_stats.get_usernames_with_stats()
            user_infos = list()
            for username in usernames:
                user = User.get_user(username)
                user_infos.append(self.build_user_info(user))
            user_infos = sorted(user_infos)
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
                user_data_list.append(user_result)
        return user_data_list, estimated_consumption_time

    def _do_call(self):
        options = self.options
        user_data_list, estimated_consumption_time = self._get_stats()
        options['user_data'] = user_data_list
        options['estimated_consumption_time'] = estimated_consumption_time
        options.update(self._get_top_header_options())
        return options

    def __call__(self):
        self._check_access()
        return self._do_call()


@view_config(route_name='objects.generic.traversal',
             context=IContentPackageBundle,
             name=VIEW_BOOK_PROGRESS_REPORT,
             accept='text/csv',
             request_param=not_('format'))
@view_config(route_name='objects.generic.traversal',
             context=IContentPackageBundle,
             name=VIEW_BOOK_PROGRESS_REPORT,
             request_param='format=text/csv')
class BookProgressReportCSV(BookProgressReportPdf, ReportCSVMixin):

    @Lazy
    def header_field_map(self):
        return {
            'Name': 'display_name',
            'Username': 'username',
            'Email': 'email',
            'Progress (min)': 'progress_min',
            'Progress Required (min)': 'progress_required_min',
            'Last Accessed': 'last_accessed'
        }

    @Lazy
    def header_row(self):
        return ('Name', 'Username', 'Email',
                'Progress (min)', 'Progress Required (min)', 'Last Accessed')

    def _get_report_data(self):
        user_data_list, estimated_consumption_time = self._get_stats()
        result = []
        # Map this into our header dict
        # total_view_time is in min
        for user_stat in user_data_list or ():
            result.append({'display_name': user_stat.userinfo.display,
                           'username': user_stat.userinfo.username,
                           'email': user_stat.userinfo.email,
                           'progress_min': user_stat.total_view_time,
                           'progress_required_min': estimated_consumption_time,
                           'last_accessed': user_stat.last_accessed})
        return result

    @property
    def filename(self):
        return self._build_filename([self.book_filename_part], extension='.csv')

    def _do_call(self):
        return self._do_create_response(filename=self.filename)


_UserConceptProgressStat = \
    namedtuple('UserConceptProgressStat',
               ('userinfo', 'total_view_time', 'last_accessed', 'is_complete'))

_ConceptProgressStat = \
    namedtuple('ConceptProgressStat',
               ('concept_ntiid', 'concept_name', 'concept_estimated_time', 'user_data'))


@view_config(route_name='objects.generic.traversal',
             context=IContentPackageBundle,
             name=VIEW_BOOK_CONCEPT_REPORT,
             accept='application/pdf',
             request_param=not_('format'))
@view_config(route_name='objects.generic.traversal',
             context=IContentPackageBundle,
             name=VIEW_BOOK_CONCEPT_REPORT,
             request_param='format=application/pdf')
class BookConceptReportPdf(BookProgressReportPdf):
    """
    Extending our book progress report. This report will want to
    get user progress on each `concept` contained within this book.
    This book must have concepts defined (e.g. concepts.json) or we
    have nothing to do.

    Options should have:

    <concept_data> = {concept_name, concept_estimated_time, user_data}
    """

    report_title = _(u'Standards Progress Report')

    def _get_concept_estimated_access_time(self, values, concepts):
        """
        This method return concepts_metrics dictionary that contains information
        about estimated reading time for each concept (represented by concept ntiid).
        concept_metrics looks as follow:
        {u'tag:nextthought.com,2011-10:IFSTA-NTIConcept-sample_book.concept.concept:NFPA_1072':
            {
                'normalized_estimated_reading_time': 0,
                'name': u'NFPA 1072',
                'estimated_reading_time': 0
             },
        u'tag:nextthought.com,2011-10:IFSTA-NTIConcept-sample_book.concept.concept:math':
            {
                'normalized_estimated_reading_time': 30,
                'name': u'math',
                'estimated_reading_time': 3.165
            }
        }
        """
        cumetrics = component.getUtility(IContentUnitMetrics)
        metrics = cumetrics.process(self.context)
        cmtime = ContentConsumptionTime(metrics, values)
        certime = ConceptsEstimatedReadingTime(concepts, cmtime)
        concepts_metrics = certime.process()
        return concepts_metrics

    def _get_concept_tree_usage(self, concepts_hierarchy, ntiid_stats_map):
        """
        Method to get usage statistic (total_view_time) on each concept per user.
        It return concepts_usage dictionary that looks as follow:
        {
        'concept_ntiid_1': {
                'usage' : {...},
                'name'  : '...'}
                },
        'concept_ntiid_2': {
                'usage' : {...},
                'name'  : '...'
                },
        ...
        }
        For example:
        {u'tag:nextthought.com,2011-10:IFSTA-NTIConcept-IFSTA_Book_Aircraft_Rescue_and_Fire_Fighting_Sixth_Edition.concept.concept:NFPA_1003': {
            'usages': {u'dortje': 0, u'brownie': 0, u'brownie3': 0},
            'name': u'NFPA 1003'
            },
        u'tag:nextthought.com,2011-10:IFSTA-NTIConcept-IFSTA_Book_Aircraft_Rescue_and_Fire_Fighting_Sixth_Edition.concept.concept:NFPA_1002': {
            'usages': {},
            'name': u'NFPA 1002'
            }
        }
        """
        if 'concepthierarchy' not in concepts_hierarchy:
            return None
        tree = concepts_hierarchy['concepthierarchy']
        concepts_usage = {}
        if 'concepts' in tree:
            concepts = tree['concepts']
            if 'name' not in concepts and 'concepts' in concepts:
                concepts = concepts['concepts']
            for concept_ntiid, concept in concepts.items():
                self._process_concept_tree(ntiid_stats_map, concept_ntiid, concept, concepts_usage)
        return concepts_usage

    def _process_concept_tree(self, ntiid_stats_map, concept_ntiid, concept, concepts_usage):
        """
        This method recursively traverse concept and its subconcepts.
        While traversing, the concepts_usage dictionary is updated with the
        information about users's total time view on each concept as well
        as the last accessed time for that concept.
        Users' total view time is acquired from ntiid_stats_map which is
        dictionary with content unit ntiids as its keys and
        nti.app.analytics.usage_stats.ResourceStats objects as its values.
        Please check comment on method _get_concept_tree_usage to see the
        structure of concepts_usage.
        """
        cusage = {}
        cusage['name'] = concept['name']
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
        @param ntiid_stats_map    : key is content unit ntiid and value is nti.app.analytics.usage_stats.ResourceStats object
        @rtype : dictionary
        @return: (total time spent on a concept by user, user last_view_time)
        """
        user_concept_stats = {}
        for unit_ntiid in content_unit_ntiids:
            # Get data for our unit as well as any children for our unit
            content_unit = find_object_with_ntiid(unit_ntiid)
            for content_item in itertools.chain((content_unit,),
                                                 content_unit.children):
                content_ntiid = content_item.ntiid
                if content_ntiid in ntiid_stats_map:
                    user_stats = ntiid_stats_map[content_ntiid].user_stats
                    for s_user, user_stat in user_stats.items():
                        total_view_time = user_stat.total_view_time
                        if total_view_time:
                            # Ok, append our total_view times
                            if s_user in user_concept_stats and user_concept_stats[s_user]:
                                total_view_time += user_concept_stats[s_user][0]
                        elif s_user in user_concept_stats:
                            # Use our existing time
                            total_view_time = user_concept_stats[s_user][0]

                        # Now the last_accessed time
                        unit_last_view_time = getattr(user_stat, 'last_view_time')
                        if unit_last_view_time:
                            # We have a time; if we have a current last time, compare and
                            # take the max. Otherwise, this is our new basis.
                            if s_user in user_concept_stats:
                                current_last_view_time = user_concept_stats[s_user][1]
                                if current_last_view_time:
                                    unit_last_view_time = max(current_last_view_time,
                                                              unit_last_view_time)
                        elif s_user in user_concept_stats:
                            # Use our existing time
                            unit_last_view_time = user_concept_stats[s_user][1]
                        user_concept_stats[s_user] = (total_view_time, unit_last_view_time)
        return user_concept_stats

    def _aggregate_concept_usage(self, cparent_ntiid, cchild_ntiid, concepts_usage):
        """
        This method aggregate users usage (total view time, last_accessed)
        from sub/child concept to parent concept
        """
        for user in concepts_usage[cchild_ntiid]['usages']:
            if user not in concepts_usage[cparent_ntiid]['usages']:
                concepts_usage[cparent_ntiid]['usages'][user] = concepts_usage[cchild_ntiid]['usages'][user]
            else:
                parent_total_view_time, parent_last_accessed = concepts_usage[cparent_ntiid]['usages'][user]
                total_view_time, last_accessed = concepts_usage[cchild_ntiid]['usages'][user]
                new_view_time = parent_total_view_time + total_view_time
                if last_accessed and parent_last_accessed:
                    new_last_accessed = max(last_accessed, parent_last_accessed)
                elif last_accessed:
                    new_last_accessed = last_accessed
                elif parent_last_accessed:
                    new_last_accessed = parent_last_accessed
                concepts_usage[cparent_ntiid]['usages'][user] = (new_view_time, new_last_accessed)

    def _map_all_usernames_to_concepts_usage(self, usernames, concepts_usage):
        """
        This method is to update users in concepts_usage.
        usernames list consists of all the book's usernames.
        However the concept['usage'] only list users that already read the
        particular unit where the concept is refered.
        We want to include all users in the concept['usage'] for the reporting.

        For example:

        Before running this method, concepts_usage looks as follow:
        {u'tag:nextthought.com,2011-10:IFSTA-NTIConcept-IFSTA_Book_Aircraft_Rescue_and_Fire_Fighting_Sixth_Edition.concept.concept:NFPA_1003': {
            'usages': {u'dortje': (3, <last_accessed>), u'brownie': (3, <last_accessed>), u'brownie3': (85, <last_accessed>)},
            'name': u'NFPA 1003'
            },
        u'tag:nextthought.com,2011-10:IFSTA-NTIConcept-IFSTA_Book_Aircraft_Rescue_and_Fire_Fighting_Sixth_Edition.concept.concept:NFPA_1002': {
            'usages': {},
            'name': u'NFPA 1002'
            }
        }

        After running this method, concepts_usage looks as follow:
        {u'tag:nextthought.com,2011-10:IFSTA-NTIConcept-IFSTA_Book_Aircraft_Rescue_and_Fire_Fighting_Sixth_Edition.concept.concept:NFPA_1003': {
            'usages': {u'dortje': (3, <last_accessed>), u'brownie': (3, <last_accessed>), u'brownie3': (85, <last_accessed>), u'tandirura': (0, None)},
            'name': u'NFPA 1003'
            },
        u'tag:nextthought.com,2011-10:IFSTA-NTIConcept-IFSTA_Book_Aircraft_Rescue_and_Fire_Fighting_Sixth_Edition.concept.concept:NFPA_1002': {
            'usages': {u'dortje': (0, <last_accessed>), u'brownie': (0, <last_accessed>), u'brownie3': (0, <last_accessed>), u'tandirura': (0, None)},
            'name': u'NFPA 1002'
            }
        }
        """
        users = set(usernames)
        for concept in list(concepts_usage.values()):
            usage = concept['usages']
            users_in_usage = set(usage.keys())
            users_not_in_usage = users - users_in_usage
            users_not_in_usage_dict = {username: (0, None) for username in users_not_in_usage}
            usage.update(users_not_in_usage_dict)

    def _check_user_completion_on_a_concept(self, concept, estimated_consumption_time):
        """
        This method check if a user already spends time reading a concept more
        than estimated consumption/reading time. The method returns a list of
        namedtuple _UserConceptProgressStat that consist of user_info,
        total_view_time in minutes floored to 15 minutes mark and a boolean is_complete.
        """
        user_infos = list()
        usages = concept['usages']
        for username in usages:
            user = User.get_user(username)
            user_infos.append(self.build_user_info(user))
        user_infos = sorted(user_infos)
        user_data = list()
        for user_info in user_infos:
            total_view_time, last_accessed = usages[user_info.username]
            total_view_time = self._get_total_view_time_in_minutes(total_view_time)
            is_complete = estimated_consumption_time \
                      and total_view_time >= estimated_consumption_time
            user_result = _UserConceptProgressStat(user_info,
                                                   total_view_time,
                                                   last_accessed,
                                                   is_complete)
            user_data.append(user_result)
        return user_data

    def _get_total_view_time_in_minutes(self, total_view_time):
        """
        Total view time obtain from ntiid_stats_map is in second. We want to
        set it to minutes and floor it to 15 minutes mark.
        """
        result = 0
        if total_view_time:
            in_minutes = total_view_time / 60
            in_base = floor(in_minutes / self.VIEW_TIME_MINUTE_FLOOR)
            result = int(in_base * self.VIEW_TIME_MINUTE_FLOOR)
        return result

    def _get_stats(self):
        self._check_content_metrics()
        values = self.readInput()
        book_stats = IResourceUsageStats(self.book, None)

        uconcepts = component.getUtility(IConcepts)
        concepts_hierarchy = uconcepts.process(self.context)
        concepts_metrics = self._get_concept_estimated_access_time(values, concepts_hierarchy)
        result = list()
        if book_stats and concepts_hierarchy:
            usernames = book_stats.get_usernames_with_stats()
            accum = book_stats.accum
            ntiid_stats_map = accum.ntiid_stats_map
            concepts_usage = self._get_concept_tree_usage(concepts_hierarchy, ntiid_stats_map)
            self._map_all_usernames_to_concepts_usage(usernames, concepts_usage)

            for concept_ntiid, concept in concepts_usage.items():
                estimated_consumption_time_in_minutes = concepts_metrics[concept_ntiid]['normalized_estimated_reading_time']
                user_data = self._check_user_completion_on_a_concept(concept,
                                                                     estimated_consumption_time_in_minutes)
                concept_name = concept['name']
                concept_result = _ConceptProgressStat(concept_ntiid,
                                                      concept_name,
                                                      estimated_consumption_time_in_minutes,
                                                      user_data)
                result.append(concept_result)
        result = sorted(result, key=lambda x: x.concept_name.lower())
        return result

    def _do_call(self):
        options = self.options
        concept_data = self._get_stats()
        options['concept_data'] = concept_data
        options.update(self._get_top_header_options())
        return options

    def __call__(self):
        self._check_access()
        return self._do_call()


@view_config(route_name='objects.generic.traversal',
             context=IContentPackageBundle,
             name=VIEW_BOOK_CONCEPT_REPORT,
             accept='text/csv',
             request_param=not_('format'))
@view_config(route_name='objects.generic.traversal',
             context=IContentPackageBundle,
             name=VIEW_BOOK_CONCEPT_REPORT,
             request_param='format=text/csv')
class BookConceptReportCSV(BookProgressReportPdf, ReportCSVMixin):

    @Lazy
    def _stats(self):
        return self._get_stats()

    @Lazy
    def _concept_names(self):
        # These are sorted
        return [x.concept_name for x in self._stats]

    @Lazy
    def header_field_map(self):
        result = {
            'Name': 'display_name',
            'Username': 'username',
            'Email': 'email',
        }
        for concept_name in self._concept_names:
            for header, field in (('Progress (min)', 'progress_min'),
                                  ('Progress Required (min)', 'progress_required_min'),
                                  ('Last Accessed', 'last_accessed')):
                result['%s %s' % (concept_name, header)] = '%s_%s' % (concept_name, field)
        return result

    @Lazy
    def header_row(self):
        result = ['Name', 'Username', 'Email']
        for concept_name in self._concept_names:
            for header in ('Progress (min)', 'Progress Required (min)', 'Last Accessed'):
                result.append('%s %s' % (concept_name, header))
        return result

    # FIXME remove
    _UserConceptProgressStat = \
        namedtuple('UserConceptProgressStat',
               ('userinfo', 'total_view_time', 'last_accessed', 'is_complete'))

    _ConceptProgressStat = \
        namedtuple('ConceptProgressStat',
               ('concept_ntiid', 'concept_name', 'concept_estimated_time', 'user_data'))

    def _get_report_data(self):
        result = []
        # The stats we get our grouped by concept, but we'll want to return user rows.
        # Map this into our header dict
        # total_view_time is in min
        if self._stats:
            # All of these user_infos *should* be the same length, with empty data
            # if users do not have data for a concept. Therefore, we arbitrarily
            # iterate over the first user info set.
            # Should be sorted by last_name, first_name.
            user_info_one = self._stats[0].user_data
            for idx, user_data in user_info_one:
                userinfo = user_data.userinfo
                user_row = {'display_name': userinfo.display,
                            'username': userinfo.username,
                            'email': userinfo.email}
                for concept_data in self._stats:
                    # Get the user_data for our index and validate everything lines up
                    user_data = concept_data.user_data[idx]
                    assert userinfo.username == user_data.userinfo.username
                    concept_name = concept_data.concept_name
                    user_row['%s_progress_min' % concept_name] = user_data.total_view_time
                    user_row['%s_progress_required_min' % concept_name] = concept_data.concept_estimated_time
                    user_row['%s_last_accessed' % concept_name] = user_data.last_accessed
                result.append(user_row)
        return result

    @property
    def filename(self):
        return self._build_filename([self.book_filename_part], extension='.csv')

    def _do_call(self):
        return self._do_create_response(filename=self.filename)
