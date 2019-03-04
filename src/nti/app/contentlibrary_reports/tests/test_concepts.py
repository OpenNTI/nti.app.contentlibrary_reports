#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_entries

import os
import json
import math
import unittest

from nti.app.contentlibrary_reports.concepts import Concepts
from nti.app.contentlibrary_reports.concepts import ConceptsEstimatedReadingTime
from nti.app.contentlibrary_reports.content_metrics import ContentConsumptionTime

from nti.app.contentlibrary_reports.interfaces import IConcepts
from nti.testing.matchers import verifiably_provides


class TestConcepts(unittest.TestCase):

  def test_concepts(self):
    concepts = Concepts()
    assert_that(concepts, verifiably_provides(IConcepts))


class TestConceptsEstimatedReadingTime(unittest.TestCase):
  def data_file(self, name):
    return os.path.join(os.path.dirname(__file__), 'data', name)

  def test_concepts_estimated_reading_time(self):
    concepts_file = 'concepts.json'
    content_metrics_file = 'content_metrics.json'

    with open(self.data_file(content_metrics_file)) as fp:
      content_metrics = json.load(fp)
    tparams = {'minute_block': 15,
               'wpm': 200,
               'figure_n_word': 0,
               'table_n_word': 0,
               'image_n_word': 0}
    cmtime = ContentConsumptionTime(content_metrics, tparams)
    with open(self.data_file(concepts_file)) as fp:
      concepts_hierarchy = json.load(fp)

    certime = ConceptsEstimatedReadingTime(concepts_hierarchy, cmtime)
    concepts_metrics = certime.process()
    concept_1_ntiid = "tag:nextthought.com,2011-10:IFSTA-NTIConcept-sample_book.concept.concept:NFPA_1072"
    concept_2_ntiid = "tag:nextthought.com,2011-10:IFSTA-NTIConcept-sample_book.concept.concept:math"

    chapter_1_ntiid = "tag:nextthought.com,2011-10:IFSTA-HTML-sample_book.chapter:1"
    chapter_2_ntiid = "tag:nextthought.com,2011-10:IFSTA-HTML-sample_book.chapter:2"

    chapter_1_reading_time_in_minutes = cmtime.get_total_minutes(chapter_1_ntiid)
    chapter_2_reading_time_in_minutes = cmtime.get_total_minutes(chapter_2_ntiid)

    assert_that(concepts_metrics, has_entries(concept_1_ntiid,
                                              has_entries('name', is_(u'NFPA 1072'),
                                                          'estimated_reading_time', is_(0)
                                                          )
                                              )
                )
    assert_that(concepts_metrics, has_entries(concept_2_ntiid,
                                              has_entries('name', is_(u'math'),
                                                          'estimated_reading_time', is_(chapter_1_reading_time_in_minutes + chapter_2_reading_time_in_minutes))
                                              )
                )

    chapter_1_normalized_reading_time_in_minutes = cmtime.get_normalize_estimated_time_in_minutes(chapter_1_ntiid)
    chapter_2_normalized_reading_time_in_minutes = cmtime.get_normalize_estimated_time_in_minutes(chapter_2_ntiid)
    total_normalized_reading_time_in_minutes = chapter_1_normalized_reading_time_in_minutes + chapter_2_normalized_reading_time_in_minutes

    assert_that(concepts_metrics, has_entries(concept_2_ntiid,
                                              has_entries('name', is_(u'math'),
                                                          'normalized_estimated_reading_time', is_(total_normalized_reading_time_in_minutes))
                                              )
                )

  def test_concepts_estimated_reading_time_2(self):
    concepts_file = 'concepts2.json'
    content_metrics_file = 'content_metrics2.json'

    with open(self.data_file(content_metrics_file)) as fp:
      content_metrics = json.load(fp)
    tparams = {'minute_block': 15,
               'wpm': 200,
               'figure_n_word': 0,
               'table_n_word': 0,
               'image_n_word': 0}
    cmtime = ContentConsumptionTime(content_metrics, tparams)
    with open(self.data_file(concepts_file)) as fp:
      concepts_hierarchy = json.load(fp)

    certime = ConceptsEstimatedReadingTime(concepts_hierarchy, cmtime)
    concepts_metrics = certime.process()

    concept_1_ntiid = "tag:nextthought.com,2011-10:IFSTA-NTIConcept-IFSTA_Book_Aircraft_Rescue_and_Fire_Fighting_Sixth_Edition.concept.concept:NFPA_1003"

    assert_that(concepts_metrics, has_entries(concept_1_ntiid, has_entries('name', is_("NFPA 1003"))))

    concept_2_ntiid = "tag:nextthought.com,2011-10:IFSTA-NTIConcept-IFSTA_Book_Aircraft_Rescue_and_Fire_Fighting_Sixth_Edition.concept.concept:NFPA_1002"

    chapter_10_ntiid = "tag:nextthought.com,2011-10:IFSTA-HTML-IFSTA_Book_Aircraft_Rescue_and_Fire_Fighting_Sixth_Edition.chapter:10"

    chapter_10_reading_time_in_minutes = cmtime.get_total_minutes(chapter_10_ntiid)

    chapter_10_normalized_reading_time_in_minutes = cmtime.get_normalize_estimated_time_in_minutes(chapter_10_ntiid)

    assert_that(concepts_metrics, has_entries(concept_2_ntiid,
                                              has_entries('name', is_(u'NFPA 1002'),
                                                          'normalized_estimated_reading_time', is_(chapter_10_normalized_reading_time_in_minutes),
                                                          'estimated_reading_time', is_(chapter_10_reading_time_in_minutes)
                                                          )
                                              )
                )
