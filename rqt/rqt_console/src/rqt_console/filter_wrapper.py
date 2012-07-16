# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
from qt_gui.qt_binding_helper import loadUi

from filter_wrapper_widget import FilterWrapperWidget
from severity_filter import SeverityFilter

# This class knows how to talk to all the available filter types and load the
# non-specific ui elements
class FilterWrapper:
    def __init__(self):
        #TODO it needs to get a param with the type of filter
        #Once we get more than one we are going to need some logic and a factory
        self._widget = FilterWrapperWidget()
        self._filter = SeverityFilter()
        self._widget.layout_frame.insertWidget(1, self._filter.get_widget())
        
        #TODO link the delete_button to a signal that will delete this filter entirely
        # and delete the row the catcher in filter_interface should in turn emit
        # a signal so we can remove it from the table in console_widget

    def message_test(self, message):
        return self._filter.message_test(message)

    def get_widget(self):
        return self._widget

    def is_enabled(self):
        return self._widget.enabled_checkbox.isChecked()