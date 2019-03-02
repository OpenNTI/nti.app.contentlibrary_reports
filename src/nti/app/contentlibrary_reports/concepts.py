#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import math

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
                for concept_ntiid, concept in concepts.items():
                    self._traverse_concept_tree(concept_ntiid, concept, concepts_metrics)
        return concepts_metrics

    def _traverse_concept_tree(self, concept_ntiid, concept, concepts_metrics):
        cmetrics = {}
        cmetrics['name'] = concept['name']
        self._count_estimated_reading_time(cmetrics, concept['contentunitntiids'])
        concepts_metrics[concept_ntiid] = cmetrics
        if 'concepts' in concept:
            subconcepts = concept['concepts']
            for subconcept_ntiid, subconcept in subconcepts.items():
                self._traverse_concept_tree(subconcept_ntiid, subconcept, concepts_metrics)
                self._rollup_estimated_reading_time(concept_ntiid, subconcept_ntiid, concepts_metrics)

    def _count_estimated_reading_time(self, cmetric, content_unit_ntiids):
        cmetric['normalized_estimated_reading_time'] = 0
        cmetric['estimated_reading_time'] = 0
        for unit_ntiid in content_unit_ntiids:
            cmetric['normalized_estimated_reading_time'] += self.cmtime.get_normalize_estimated_time_in_minutes(unit_ntiid)
            cmetric['estimated_reading_time'] += self.cmtime.get_total_minutes(unit_ntiid)

    def _rollup_estimated_reading_time(self, cparent_ntiid, cchild_ntiid, concepts_metrics):
        concepts_metrics[cparent_ntiid]['normalized_estimated_reading_time'] += concepts_metrics[cchild_ntiid]['normalized_estimated_reading_time']
        concepts_metrics[cparent_ntiid]['estimated_reading_time'] += concepts_metrics[cchild_ntiid]['estimated_reading_time']
