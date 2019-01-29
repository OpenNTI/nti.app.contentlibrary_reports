#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import math

from zope import component
from zope import interface

from nti.app.contentlibrary_reports.interfaces import IContentUnitMetrics

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IContentUnitMetrics)
class ContentUnitMetrics(object):
    def __init__(self, context):
        self.context = context

    def process(self):
        fs_root = self.context.ContentPackages[0]
        sibling = fs_root.make_sibling_key('content_metrics.json')
        content_metrics = sibling.readContentsAsJson()
        return content_metrics


class ContentConsumptionTime(object):
    WPM = 200
    BLOCK_PER_MIN = 15
    FIGURE_COUNT = 1
    TABLE_COUNT = 1
    NON_FIGURE_IMAGE_COUNT = 1

    def __init__(self, metrics, tparams):
        self.content_metrics = metrics
        if 'wpm' in tparams.keys():
            self.wpm = int(tparams['wpm'])
        else:
            self.wpm = self.WPM

        if 'block_per_min' in tparams.keys():
            self.block_per_min = tparams['block_per_min']
        else:
            self.block_per_min = self.BLOCK_PER_MIN

        if 'figure_n_word' in tparams.keys():
            self.figure_n_word = tparams['figure_n_word']
        else:
            self.figure_n_word = self.FIGURE_COUNT

        if 'table_n_word' in tparams.keys():
            self.table_n_word = tparams['table_n_word']
        else:
            self.table_n_word = self.TABLE_COUNT

        if 'image_n_word' in tparams.keys():
            self.image_n_word = tparams['image_n_word']
        else:
            self.image_n_word = self.NON_FIGURE_IMAGE_COUNT

    def get_total_word_count(self, ntiid):
        return self.content_metrics[ntiid]['total_word_count']

    def get_total_word_with_block_element_detail_count(self, ntiid):
        unit = self.content_metrics[ntiid]
        details = self._get_block_element_detail(unit)
        total_words = unit['total_word_count'] \
            + sum([details[key] for key in details])
        return total_words

    def get_total_minutes(self, ntiid):
        total_words = self.get_total_word_with_block_element_detail_count(ntiid)
        minutes = float(total_words) / float(self.wpm)
        return minutes

    def get_minutes_nblocks(self, ntiid):
        minutes = self.get_total_minutes(ntiid)
        nblocks = minutes / self.block_per_min
        return nblocks

    def get_normalize_estimated_time_in_minutes(self, ntiid):
        nblocks = self.get_minutes_nblocks(ntiid)
        minutes = math.ceil(nblocks) * self.block_per_min
        return minutes

    def get_normalize_estimated_time_in_hours(self, ntiid):
        return self.get_normalize_estimated_time_in_minutes / 60

    def get_total_hours(self, ntiid):
        return self.get_total_minutes(ntiid) / 60

    def _get_block_element_detail(self, el):
        detail_dict = {}

        fig_count = el["BlockElementDetails"]['figure']['count']
        detail_dict['figure_count_word'] = fig_count * self.figure_n_word

        table_count = el["BlockElementDetails"]['table']['count']
        detail_dict['table_count_word'] = table_count * self.table_n_word

        image_count = el["non_figure_image_count"]
        detail_dict["non_figure_image_word_count"] = image_count * self.image_n_word
        return detail_dict
