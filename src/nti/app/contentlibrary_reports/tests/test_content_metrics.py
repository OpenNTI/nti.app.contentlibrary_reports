#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import assert_that
from hamcrest import is_

import os
import json
import math
import unittest

from nti.app.contentlibrary_reports.content_metrics import ContentUnitMetrics
from nti.app.contentlibrary_reports.content_metrics import ContentConsumptionTime

from nti.app.contentlibrary_reports.interfaces import IContentUnitMetrics
from nti.testing.matchers import verifiably_provides


class TestContentUnitMetrics(unittest.TestCase):

    def test_content_unit_metrics(self):
        cmetrics = ContentUnitMetrics()
        assert_that(cmetrics, verifiably_provides(IContentUnitMetrics))


class TestContentConsumptionTime(unittest.TestCase):
    def data_file(self, name):
        return os.path.join(os.path.dirname(__file__), 'data', name)

    def test_content_consumption_time(self):
        name = 'content_metrics.json'
        with open(self.data_file(name)) as fp:
            content_metrics = json.load(fp)
        tparams = {'minute_block': 15,
                   'wpm': 200,
                   'figure_n_word': 0,
                   'table_n_word': 0,
                   'image_n_word': 0}

        ctime = ContentConsumptionTime(content_metrics, tparams)

        book_ntiid = "tag:nextthought.com,2011-10:IFSTA-HTML-sample_book.sample_book"
        chapter1_ntiid = "tag:nextthought.com,2011-10:IFSTA-HTML-sample_book.chapter:1"
        chapter2_ntiid = "tag:nextthought.com,2011-10:IFSTA-HTML-sample_book.chapter:2"

        book_estimated_minutes = float(content_metrics[book_ntiid]['total_word_count']) / float(tparams['wpm'])
        assert_that(book_estimated_minutes, is_(ctime.get_total_minutes(book_ntiid)))

        book_estimated_minutes_normalized = math.ceil(book_estimated_minutes / tparams['minute_block']) * tparams['minute_block']
        assert_that(book_estimated_minutes_normalized, is_(ctime.get_normalize_estimated_time_in_minutes(book_ntiid)))

        book_estimated_hours = book_estimated_minutes / 60
        assert_that(book_estimated_hours, is_(ctime.get_total_hours(book_ntiid)))

        book_estimated_hours_normalized = book_estimated_minutes_normalized / 60
        assert_that(book_estimated_hours_normalized, is_(ctime.get_normalize_estimated_time_in_hours(book_ntiid)))

        chapter1_estimated_minutes = float(content_metrics[chapter1_ntiid]['total_word_count']) / float(tparams['wpm'])
        assert_that(chapter1_estimated_minutes, is_(ctime.get_total_minutes(chapter1_ntiid)))

        chapter1_estimated_minutes_normalized = math.ceil(chapter1_estimated_minutes / tparams['minute_block']) * tparams['minute_block']
        assert_that(chapter1_estimated_minutes_normalized, is_(ctime.get_normalize_estimated_time_in_minutes(chapter1_ntiid)))

        chapter1_estimated_hours = chapter1_estimated_minutes / 60
        assert_that(chapter1_estimated_hours, is_(ctime.get_total_hours(chapter1_ntiid)))

        chapter1_estimated_hours_normalized = chapter1_estimated_minutes_normalized / 60
        assert_that(chapter1_estimated_hours_normalized, is_(ctime.get_normalize_estimated_time_in_hours(chapter1_ntiid)))

        chapter2_estimated_minutes = float(content_metrics[chapter2_ntiid]['total_word_count']) / float(tparams['wpm'])
        assert_that(chapter2_estimated_minutes, is_(ctime.get_total_minutes(chapter2_ntiid)))

        chapter2_estimated_minutes_normalized = math.ceil(chapter2_estimated_minutes / tparams['minute_block']) * tparams['minute_block']
        assert_that(chapter2_estimated_minutes_normalized, is_(ctime.get_normalize_estimated_time_in_minutes(chapter2_ntiid)))

        chapter2_estimated_hours = chapter2_estimated_minutes / 60
        assert_that(chapter2_estimated_hours, is_(ctime.get_total_hours(chapter2_ntiid)))

        chapter2_estimated_hours_normalized = chapter2_estimated_minutes_normalized / 60
        assert_that(chapter2_estimated_hours_normalized, is_(ctime.get_normalize_estimated_time_in_hours(chapter2_ntiid)))

        assert_that(ctime.get_normalize_estimated_time_in_minutes(book_ntiid) % tparams['minute_block'], is_(0))
        assert_that(ctime.get_normalize_estimated_time_in_minutes(chapter1_ntiid) % tparams['minute_block'], is_(0))
        assert_that(ctime.get_normalize_estimated_time_in_minutes(chapter2_ntiid) % tparams['minute_block'], is_(0))

    def test_content_consumption_time_2(self):
        name = 'content_metrics.json'
        with open(self.data_file(name)) as fp:
            content_metrics = json.load(fp)
        tparams = {'minute_block': 2,
                   'wpm': 10,
                   'figure_n_word': 0,
                   'table_n_word': 0,
                   'image_n_word': 0}

        ctime = ContentConsumptionTime(content_metrics, tparams)

        book_ntiid = "tag:nextthought.com,2011-10:IFSTA-HTML-sample_book.sample_book"
        chapter1_ntiid = "tag:nextthought.com,2011-10:IFSTA-HTML-sample_book.chapter:1"
        chapter2_ntiid = "tag:nextthought.com,2011-10:IFSTA-HTML-sample_book.chapter:2"

        book_estimated_minutes = float(content_metrics[book_ntiid]['total_word_count']) / float(tparams['wpm'])
        assert_that(book_estimated_minutes, is_(ctime.get_total_minutes(book_ntiid)))

        book_estimated_minutes_normalized = math.ceil(book_estimated_minutes / tparams['minute_block']) * tparams['minute_block']
        assert_that(book_estimated_minutes_normalized, is_(ctime.get_normalize_estimated_time_in_minutes(book_ntiid)))

        book_estimated_hours = book_estimated_minutes / 60
        assert_that(book_estimated_hours, is_(ctime.get_total_hours(book_ntiid)))

        book_estimated_hours_normalized = book_estimated_minutes_normalized / 60
        assert_that(book_estimated_hours_normalized, is_(ctime.get_normalize_estimated_time_in_hours(book_ntiid)))

        chapter1_estimated_minutes = float(content_metrics[chapter1_ntiid]['total_word_count']) / float(tparams['wpm'])
        assert_that(chapter1_estimated_minutes, is_(ctime.get_total_minutes(chapter1_ntiid)))

        chapter1_estimated_minutes_normalized = math.ceil(chapter1_estimated_minutes / tparams['minute_block']) * tparams['minute_block']
        assert_that(chapter1_estimated_minutes_normalized, is_(ctime.get_normalize_estimated_time_in_minutes(chapter1_ntiid)))

        chapter1_estimated_hours = chapter1_estimated_minutes / 60
        assert_that(chapter1_estimated_hours, is_(ctime.get_total_hours(chapter1_ntiid)))

        chapter1_estimated_hours_normalized = chapter1_estimated_minutes_normalized / 60
        assert_that(chapter1_estimated_hours_normalized, is_(ctime.get_normalize_estimated_time_in_hours(chapter1_ntiid)))

        chapter2_estimated_minutes = float(content_metrics[chapter2_ntiid]['total_word_count']) / float(tparams['wpm'])
        assert_that(chapter2_estimated_minutes, is_(ctime.get_total_minutes(chapter2_ntiid)))

        chapter2_estimated_minutes_normalized = math.ceil(chapter2_estimated_minutes / tparams['minute_block']) * tparams['minute_block']
        assert_that(chapter2_estimated_minutes_normalized, is_(ctime.get_normalize_estimated_time_in_minutes(chapter2_ntiid)))

        chapter2_estimated_hours = chapter2_estimated_minutes / 60
        assert_that(chapter2_estimated_hours, is_(ctime.get_total_hours(chapter2_ntiid)))

        chapter2_estimated_hours_normalized = chapter2_estimated_minutes_normalized / 60
        assert_that(chapter2_estimated_hours_normalized, is_(ctime.get_normalize_estimated_time_in_hours(chapter2_ntiid)))

        assert_that(ctime.get_normalize_estimated_time_in_minutes(book_ntiid) % tparams['minute_block'], is_(0))
        assert_that(ctime.get_normalize_estimated_time_in_minutes(chapter1_ntiid) % tparams['minute_block'], is_(0))
        assert_that(ctime.get_normalize_estimated_time_in_minutes(chapter2_ntiid) % tparams['minute_block'], is_(0))
