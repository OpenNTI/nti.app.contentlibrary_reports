#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import math

logger = __import__('logging').getLogger(__name__)


FIGURE_COUNT = 1
TABLE_COUNT = 1
NON_FIGURE_IMAGE_COUNT = 1

WPM = 200
BLOCK_PER_MIN = 15


class ContentUnitMetrics(object):
    def __init__(self, context):
        self.context = context
        fs_root = self.context.ContentPackages[0]
        sibling = fs_root.make_sibling_key('content_metrics.json')
        self.content_metrics = sibling.readContentsAsJson()

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
        minutes = float(total_words) / float(WPM)
        return minutes

    def get_minutes_nblocks(self, ntiid):
        minutes = self.get_total_minutes(ntiid)
        nblocks = minutes / BLOCK_PER_MIN
        return nblocks

    def get_normalize_estimated_time_in_minutes(self, ntiid):
        nblocks = self.get_minutes_nblocks(ntiid)
        minutes = math.ceil(nblocks) * BLOCK_PER_MIN
        return minutes

    def get_normalize_estimated_time_in_hours(self, ntiid):
        return self.get_normalize_estimated_time_in_minutes / 60

    def get_total_hours(self, ntiid):
        return self.get_total_minutes(ntiid) / 60

    def _get_block_element_detail(self, el):
        detail_dict = {}

        fig_count = el["BlockElementDetails"]['figure']['count']
        detail_dict['figure_count_word'] = fig_count * FIGURE_COUNT

        table_count = el["BlockElementDetails"]['table']['count']
        detail_dict['table_count_word'] = table_count * TABLE_COUNT

        image_count = el["non_figure_image_count"]
        detail_dict["non_figure_image_word_count"] = image_count * NON_FIGURE_IMAGE_COUNT
        return detail_dict
