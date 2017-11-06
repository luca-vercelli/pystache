# -*- coding -*- : utf-8

"""
This module provides command-line access to pystache.

Run this script using the -h option for command-line help.

"""
import sys
try:
    import json
except ImportError:
    # The json module is new in Python 2.6, whereas simplejson is
    # compatible with earlier versions.
    try:
        import simplejson as json
    except ImportError:
        # Raise an error with a type different from ImportError
        # as a hack around this issue:
        #   http://bugs.python.org/issue7559
        from sys import exc_info
        ex_type, ex_value, tb = exc_info()
        new_ex = Exception("%s: %s" % (ex_type.__name__, ex_value))
        raise new_ex.__class__(new_ex).with_traceback(tb)

import yaml

# The optparse module is deprecated in Python 2.7 in favor of argparse.
# However, argparse is not available in Python 2.6 and earlier.
from optparse import OptionParser
import sys, os
import csv

# We use absolute imports here to allow use of this script from its
# location in source control (e.g. for development purposes).
# Otherwise, the following error occurs:
#
#   ValueError: Attempted relative import in non-package
#
from pystache.renderer import Renderer

USAGE = """\
%prog [-hy] template [context]

Render a mustache template with the given context.

positional arguments:

  template    A filename or template string.
  context     A yaml or json filename, or a json string, or CSV filename

if context is omitted, pystache read a YAML frontmatter
as render context from standard input if not a tty.

YAML frontmatter begins with --- on a single line,
followed by YAML, ending with another --- on a single line, e.g.

---
names: [ {name: chris}, {name: mark}, {name: scott} ]
---
"""

MARKER = '---\n'  # marker for yaml sections (see mustache)

def parse_args(sys_argv, usage):
    """
    Return an OptionParser for the script.

    """
    args = sys_argv[1:]

    parser = OptionParser(usage=usage)
    parser.add_option('-v', '--version', action="store_true",
                      dest="show_version", default=False,
                      help="show version and exit")
    parser.add_option("-f", "--format", dest="format",
                  help="format of the context string of filename (choose from: 'json', 'csv'). Default is JSON, unless context is a filename with .csv extension.",
                  choices=("json","csv"))
    parser.add_option("-m", "--multiple", dest="multiple",
                  help="""render the template for each context children,
writing output to KEY file (with no warning if file already exists).
If KEY is not a key of context children, then it is used as file output name,
and suffixed with a 3 digit incremental counter.""", metavar="KEY")
    options, args = parser.parse_args(args)
    if options.show_version:
        import pystache
        print("pystache %s" % pystache.__version__)
        sys.exit(0)

    try:
        template, context = args
    except ValueError as e:
        print('ERROR: %s\n' % e)
        parser.print_help()
        exit(1)
    except UnboundLocalError as e:
        print('ERROR: %s' % e)
        exit(1)

    return template, context, options.format, options.multiple


def read_yaml_frontmatter(iterable):
    """read mustache's style YAML frontmatter from an iterable

    the iterable is expected to return text lines ending with '\n'
    """
    fm_started = False
    frontmatter = []
    for line in iterable:
        if MARKER == line:
            if fm_started:
                break
            fm_started = True
            continue
        if fm_started:
            frontmatter.append(line)
    frontmatter = ''.join(frontmatter)
    return yaml.load(frontmatter), iterable


def arg2text(arg):
    """ get text from comand line arg """
    import errno
    if not isinstance(arg, str):
        return arg.read().decode('utf-8')
    else:
        try:
            if sys.version_info[0] == 3:
                with open(arg, encoding='utf-8') as data:
                    return data.read()
            else:
                with open(arg, 'rb') as data:
                    return data.read().decode('utf-8')
        except IOError, err:
            if err.errno == errno.ENOENT:
                # not a file, assumming first arg is template literal
                return arg

def extract_context(content, greedy=False):
    if content.startswith(MARKER):
        end = content.find(MARKER, len(MARKER))
        frontmatter = content[len(MARKER):end]
        content = content[end+len(MARKER):]
        context = yaml.load(frontmatter)
    elif greedy:
        frontmatter = content
        content = None
        context = yaml.load(frontmatter)
    else:
        context = {}
    return context, content

# TODO: verify whether the setup() method's entry_points argument
# supports passing arguments to main:
#
#     http://packages.python.org/distribute/setuptools.html#automatic-script-creation
#
def main(argv=None):
    if argv is None:
        argv = sys.argv

    template, context, options = parse_args(argv, USAGE)

    if context is None and not sys.stdin.isatty():
        user_context, _ = read_yaml_frontmatter(sys.stdin)
    elif context:
        content = arg2text(context)
        user_context, _ = extract_context(content, greedy=True)
    else:
        user_context = {}

    # assuming first arg is a filename or template literal
    template = arg2text(template)
    template_context, template = extract_context(template)
    template_context.update(user_context)
    renderer = Renderer()
    rendered = renderer.render(template, template_context)
    print(rendered.encode('utf-8'))

    renderer = Renderer()

    try:
        template = renderer.load_template(template)
    except TemplateNotFoundError:
        pass

    if context.endswith(".csv") or (c_format and (c_format == "csv")):
        try:
            context = csv.DictReader(open(context, 'rb'))#, delimiter=',', quotechar='"')
        except IOError:
            print('ERROR: Could not parse context as CSV file. Check usage for input format options')
            exit(-1)            
    else:
        try:
            context = json.load(open(context))
        except IOError:
            context = json.loads(context)
        except ValueError: #likely a not well-formed JSON string, or user forgot -f csv.
            print('ERROR: Could not parse context as JSON file or text, check usage for input format options')
            exit(1)

    if (multiple):
        print ("multiple render on field %s" % multiple)
        fileName, fileExt = os.path.splitext(multiple)
        for i,c in enumerate(context):
            if multiple in c:
                f_name = str(c[multiple])
            else:                
                f_name = "%s-%03d%s" % (fileName, i, fileExt)
            with open(f_name, "w") as f: # mode "wx" could be used to prevent overwriting, + pass IOError, adding "--force" option to override.
                rendered = renderer.render(template, c)
                f.write(rendered)
                print ("%s done") % f_name
    else:
        rendered = renderer.render(template, context)
        print rendered

if __name__ == '__main__':
    main()
