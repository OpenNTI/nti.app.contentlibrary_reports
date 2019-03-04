#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import math

from collections import namedtuple

from zope import interface

from nti.app.contentlibrary_reports.interfaces import IConcepts

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IConcepts)
class Concepts(object):
    def process(self, context):
        fs_root = context.ContentPackages[0]
        sibling = fs_root.make_sibling_key('concepts.json')
        concepts = sibling.readContentsAsJson()
        return concepts


_ConceptMetric = namedtuple('ConceptMetric', ('estimated_reading_time', 'normalized_estimated_reading_time'))


class ConceptsEstimatedReadingTime(object):
    def __init__(self, concept_hierachy, cmtime):
        """
        concept_hierarcy is a dictionary loaded from concepts.json
        cmtime is an object of ContentConsumptionTime
        """
        self.concept_hierachy = concept_hierachy
        self.cmtime = cmtime

    def process(self):
        concepts_metrics = {}
        if 'concepthierarchy' in self.concept_hierachy:
            tree = self.concept_hierachy['concepthierarchy']
            if 'concepts' in tree:
                concepts = tree['concepts']
                if 'name' not in concepts and 'concepts' in concepts:
                    concepts = concepts['concepts']
                for concept_ntiid, concept in concepts.items():
                    self._traverse_concept_tree(concept_ntiid, concept, concepts_metrics)
        return concepts_metrics

    def _traverse_concept_tree(self, concept_ntiid, concept, concepts_metrics):
        cmetric = {}
        cmetric['name'] = concept['name']
        metrics = self._count_estimated_reading_time(concept['contentunitntiids'])
        cmetric['normalized_estimated_reading_time'] = metrics.normalized_estimated_reading_time
        cmetric['estimated_reading_time'] = metrics.estimated_reading_time
        concepts_metrics[concept_ntiid] = cmetric
        if 'concepts' in concept:
            subconcepts = concept['concepts']
            for subconcept_ntiid, subconcept in subconcepts.items():
                self._traverse_concept_tree(subconcept_ntiid, subconcept, concepts_metrics)
                self._rollup_estimated_reading_time(concept_ntiid, subconcept_ntiid, concepts_metrics)

    def _count_estimated_reading_time(self, content_unit_ntiids):
        """
        Method to count estimated(normalized) reading time given a list of content unit ntiids (content_unit_ntiids) where a concept is referred.
        Estimated reading time is computed based on the total number of words in a content unit. It is done by ContentConsumptionTime object.
        Normalized estimated reading time is estimated reading time round up to the nearest minute block (the default is 15).
        This method returns a namedtuple _ConceptMetric
        """
        normalized_est_rtime = 0
        est_rtime = 0
        for unit_ntiid in content_unit_ntiids:
            est_rtime += self.cmtime.get_total_minutes(unit_ntiid)
            normalized_est_rtime += self.cmtime.get_normalize_estimated_time_in_minutes(unit_ntiid)
        metrics = _ConceptMetric(est_rtime, normalized_est_rtime)
        return metrics

    def _rollup_estimated_reading_time(self, cparent_ntiid, cchild_ntiid, concepts_metrics):
        """
        This method add up estimated(normalized) reading time from a child/sub concept to its parent concept
        """
        concepts_metrics[cparent_ntiid]['normalized_estimated_reading_time'] += concepts_metrics[cchild_ntiid]['normalized_estimated_reading_time']
        concepts_metrics[cparent_ntiid]['estimated_reading_time'] += concepts_metrics[cchild_ntiid]['estimated_reading_time']
