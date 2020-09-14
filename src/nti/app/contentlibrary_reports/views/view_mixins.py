#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import csv

from datetime import datetime

from io import BytesIO

from pyramid.httpexceptions import HTTPForbidden

from zope import component

from zope.cachedescriptors.property import Lazy

from nti.app.contentlibrary_reports.interfaces import ACT_VIEW_BOOK_REPORTS

from nti.app.contenttypes.reports.views.view_mixins import AbstractReportView

from nti.appserver.pyramid_authorization import has_permission

from nti.dataserver.users.interfaces import IProfileDisplayableSupplementalFields

logger = __import__('logging').getLogger(__name__)

MAX_FILENAME_LEN = 255  # 255 char max length (OSX (APFS) and Win10 (NTFS))


class AbstractBookReportView(AbstractReportView):
    """
    An abstract report view that can be used on something that can be adapted
    to an :class:`IContentPackageBundle`.
    """

    filename_suffix = 'pdf'

    def _check_access(self):
        if not has_permission(ACT_VIEW_BOOK_REPORTS, self.book, self.request):
            raise HTTPForbidden()

    @property
    def filename(self):
        # Format: <prefix>_<title>.pdf
        # Prefix gets any portion not taken by _<title>.pdf
        prefix = self.book_name() and self.book_name()[:self._max_prefix_length]
        basename = self.report_title if not prefix else u'{0}_{1}'.format(prefix, self.report_title)
        return u'{0}.pdf'.format(basename[:self._max_title_length])

    @property
    def _max_prefix_length(self):
        # MAX less room for "_<title>.pdf"
        return max(MAX_FILENAME_LEN - (len(self.report_title) + 5), 0)

    @property
    def _max_title_length(self):
        # MAX less room for ".pdf"
        return MAX_FILENAME_LEN - 4

    @Lazy
    def book(self):
        return self.context

    def book_name(self):
        return self.book.title

    def generate_footer(self):
        date = self._adjust_date(datetime.utcnow())
        date = date.strftime('%b %d, %Y %I:%M %p')
        title = self.report_title
        book_name = self.book_name()
        return "%s %s %s %s" % (title, book_name, date, self.timezone_info_str)

    def readInput(self, value=None):
        if self.request.body:
            values = super(AbstractBookReportView, self).readInput(value)
        else:
            values = dict(self.request.params)
        return values


class ReportCSVMixin(object):

    filename_suffix = 'csv'

    @Lazy
    def supplemental_field_utility(self):
        return component.queryUtility(IProfileDisplayableSupplementalFields)

    @Lazy
    def header_field_map(self):
        raise NotImplementedError()

    @Lazy
    def header_row(self):
        raise NotImplementedError()

    def _get_report_data(self):
        raise NotImplementedError()

    def _get_supplemental_header(self):
        result = []
        if self.supplemental_field_utility:
            display_dict = self.supplemental_field_utility.get_field_display_values()
            supp_fields = self.supplemental_field_utility.get_ordered_fields()
            for supp_field in supp_fields:
                result.append(display_dict.get(supp_field))
        return result

    def _get_supplemental_data(self, user_report_data):
        data = []
        if self.supplemental_field_utility:
            supp_fields = self.supplemental_field_utility.get_ordered_fields()
            for supp_field in supp_fields:
                data.append(user_report_data.get(supp_field))
        return data

    def _create_csv_file(self, stream, report_data=None):
        """
        bytes - write the data in bytes
        """
        writer = csv.writer(stream, encoding='utf-8')
        # Header
        header_row = list(self.header_row)

        # Optional supplemental header
        header_row.extend(self._get_supplemental_header())

        if report_data is None:
            report_data = self._get_report_data()

        writer.writerow(header_row)

        for user_report_data in report_data:
            data_row = []
            for field in self.header_row:
                # Some users for this class may have placeholder columns
                # that we do not have info for.
                # If we have a field in our field_map, we *must* have a value
                # in our user data dict or it's a code error.
                if field in self.header_field_map:
                    data_row.append(user_report_data[self.header_field_map[field]])
                else:
                    data_row.append('')

            # Optional supplemental data.
            data_row.extend(self._get_supplemental_data(user_report_data))
            writer.writerow(data_row)
        stream.flush()
        stream.seek(0)

    def _do_create_response(self, filename):
        response = self.request.response
        response.content_encoding = 'identity'
        response.content_type = 'text/csv; charset=UTF-8'
        response.content_disposition = 'attachment; filename="%s"' % filename
        stream = BytesIO()
        self._create_csv_file(stream)
        response.body_file = stream
        return response
