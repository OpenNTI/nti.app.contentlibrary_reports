#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import unittest

from fudge import Fake

from hamcrest import assert_that, equal_to

from nti.app.contentlibrary_reports.views.book_views import BookProgressReportPdf

from nti.app.testing.layers import SharedConfiguringTestLayer


class TestBookViewsTitle(unittest.TestCase):
    layer = SharedConfiguringTestLayer

    def test_book_progress_report_no_title(self):
        request = Fake('request')
        book = Fake('book').has_attr(title=None)
        view = BookProgressReportPdf(book, request)
        assert_that(view.filename, equal_to('Progress Overview Report.pdf'))

    def test_book_progress_report_empty_title(self):
        request = Fake('request')
        book = Fake('book').has_attr(title='')
        view = BookProgressReportPdf(book, request)
        assert_that(view.filename, equal_to('Progress Overview Report.pdf'))

    def test_book_progress_report_long_book_title(self):
        request = Fake('request')
        book = Fake('book').has_attr(title='0123456789' * 26)
        view = BookProgressReportPdf(book, request)
        assert_that(view.filename, equal_to('{0}_Progress Overview Report.pdf'.format(book.title[:226])))

    def test_book_progress_report_long_report_title(self):
        request = Fake('request')
        book = Fake('book').has_attr(title='The Apes of Wrath')
        view = BookProgressReportPdf(book, request)
        view.report_title = '0123456789' * 26
        assert_that(view.filename, equal_to('{0}.pdf'.format(view.report_title[:251])))

    def test_book_progress_report(self):
        request = Fake('request')
        book = Fake('book').has_attr(title='The Apes of Wrath')
        view = BookProgressReportPdf(book, request)
        assert_that(view.filename, equal_to('The Apes of Wrath_Progress Overview Report.pdf'))
