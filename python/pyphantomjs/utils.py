'''
  This file is part of the PyPhantomJS project.

  Copyright (C) 2011 James Roe <roejames12@hotmail.com>

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os
import sys
import codecs
import argparse

from PyQt4.QtCore import QDateTime, Qt, QtDebugMsg, QtWarningMsg, \
                         QtCriticalMsg, QtFatalMsg, qWarning

from csconverter import CSConverter
from plugincontroller import Bunch, do_action


version_major, version_minor, version_patch = (1, 2, 0)
version = '%d.%d.%d' % (version_major, version_minor, version_patch)

license = '''
  PyPhantomJS Version %s

  Copyright (C) 2011 James Roe <roejames12@hotmail.com>

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
''' % version


def argParser():
    parser = argparse.ArgumentParser(
        description='Minimalistic headless WebKit-based JavaScript-driven tool',
        usage='%(prog)s [options] script.[js|coffee] [script argument [script argument ...]]',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument('script', metavar='script.[js|coffee]', nargs='?',
        help='The script to execute, and any args to pass to it'
    )

    parser.add_argument('--disk-cache', default='no',
        choices=['yes', 'no'],
        help='Enable disk cache (default: %(default)s)'
    )
    parser.add_argument('--ignore-ssl-errors', default='no',
        choices=['yes', 'no'],
        help='Ignore SSL errors (default: %(default)s)'
    )
    parser.add_argument('--load-images', default='yes',
        choices=['yes', 'no'],
        help='Load all inlined images (default: %(default)s)'
    )
    parser.add_argument('--load-plugins', default='no',
        choices=['yes', 'no'],
        help='Load all plugins (i.e. Flash, Silverlight, ...) (default: %(default)s)'
    )
    parser.add_argument('--local-access-remote', default='no',
        choices=['yes', 'no'],
        help='Local content can access remote URL (default: %(default)s)'
    )
    parser.add_argument('--proxy', metavar='address:port',
        help='Set the network proxy'
    )
    parser.add_argument('-v', '--verbose', action='store_true',
        help='Show verbose debug messages'
    )
    parser.add_argument('--version',
        action='version', version=license,
        help='show this program\'s version and license'
    )

    do_action('ArgParser', Bunch(locals()))

    return parser


coffeeScriptConverter = None
def coffee2js(script):
    global coffeeScriptConverter

    # We need only one instance of the CSConverter to survive for the whole life of PyPhantomJS
    if not coffeeScriptConverter:
        coffeeScriptConverter = CSConverter()

    return coffeeScriptConverter.convert(script)


def injectJsInFrame(filePath, libraryPath, targetFrame, startingScript=False):
    try:
        # if file doesn't exist in the CWD, use the lookup
        if not os.path.exists(filePath):
            filePath = os.path.join(libraryPath, filePath)

        with codecs.open(filePath, encoding='utf-8') as f:
            script = f.read()

        if script.startswith('#!') and not filePath.lower().endswith('.coffee'):
            script = '//' + script

        if filePath.lower().endswith('.coffee'):
            result = coffee2js(script)
            if result[0] is False:
                if startingScript:
                    sys.exit(result[1])
                else:
                    qWarning(result[1])
                    script = ''
            else:
                script = result[1]

        targetFrame.evaluateJavaScript(script)
        return True
    except IOError:
        qWarning('No such file or directory: \'%s\'' % filePath)
        return False


class MessageHandler:
    def __init__(self, verbose):
        self.verbose = verbose

    def process(self, msgType, msg):
        now = QDateTime.currentDateTime().toString(Qt.ISODate)

        if msgType == QtDebugMsg:
            if self.verbose:
                print '%s [DEBUG] %s' % (now, msg)
        elif msgType == QtWarningMsg:
            print >> sys.stderr, '%s [WARNING] %s' % (now, msg)
        elif msgType == QtCriticalMsg:
            print >> sys.stderr, '%s [CRITICAL] %s' % (now, msg)
        elif msgType == QtFatalMsg:
            print >> sys.stderr, '%s [FATAL] %s' % (now, msg)


class SafeStreamFilter(object):
    '''Convert string to something safe'''
    def __init__(self, target):
        self.target = target
        self.encoding = 'utf-8'
        self.errors = 'replace'
        self.encode_to = self.target.encoding or 'utf-8'

    def write(self, s):
        s = self.encode(s)
        self.target.write(s)

    def flush(self):
        self.target.flush()

    def encode(self, s):
        return s.encode(self.encode_to, self.errors).decode(self.encode_to)
