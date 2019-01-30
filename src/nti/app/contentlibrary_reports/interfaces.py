#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.security.permission import Permission

ACT_VIEW_BOOK_REPORTS = Permission('nti.actions.contentlibrary_reports.view_reports')


class IContentUnitMetrics(interface.Interface):
    """
    An interface for utility to get content_metrics.json from content package
    content_metrics.json use content unit ntiid for as.
    each key has dictionary value for example:
    "tag:nextthought.com,2011-10:IFSTA-HTML-sample_book.sample_book": {
        "BlockElementDetails": {
            "figure": {
                "count": 2,
                "sentence_count": 2,
                "char_count": 40,
                "word_count": 8,
                "non_whitespace_char_count": 34
            },
            "glossary": {
                "count": 1,
                "sentence_count": 1,
                "char_count": 208,
                "word_count": 30,
                "non_whitespace_char_count": 179
            },
            "sidebar_caution": {
                "count": 1,
                "sentence_count": 2,
                "char_count": 135,
                "word_count": 21,
                "non_whitespace_char_count": 115
            },
            "table": {
                "count": 1,
                "sentence_count": 1,
                "char_count": 143,
                "word_count": 17,
                "non_whitespace_char_count": 80
            },
            "sidebar_warning": {
                "count": 1,
                "sentence_count": 5,
                "char_count": 173,
                "word_count": 24,
                "non_whitespace_char_count": 150
            },
            "sidebar_note": {
                "count": 1,
                "sentence_count": 1,
                "char_count": 70,
                "word_count": 10,
                "non_whitespace_char_count": 61
            }
        },
        "total_sentence_count": 54,
        "expected_consumption_time": null,
        "char_count": 3117,
        "total_word_count": 633,
        "avg_word_per_sentence": 12.452380952380953,
        "avg_word_per_paragraph": 30.764705882352942,
        "word_count": 523,
        "non_whitespace_char_count": 2539,
        "unique_percentage_of_word_count": 0.5086042065009561,
        "length_of_the_shortest_word": 1,
        "length_of_the_longest_word": 13,
        "total_non_whitespace_char_count": 3158,
        "sentence_count": 42,
        "non_figure_image_count": 0,
        "paragraph_count": 17,
        "total_char_count": 3886,
        "unique_word_count": 266
    }
    """
