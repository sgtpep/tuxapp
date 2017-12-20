# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import functools
import re

from lib import (
  appfile,
  testing,
  tuxapp,
  utilities,
)

def reword_assertion(message):
  def decorator(function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
      try:
        return function(*args, **kwargs)
      except AssertionError as exception:
        reworded_message = exception.args[0][0].lower() + exception.args[0][1:] if exception.args else 'unknown error'
        built_message = tuxapp.build_decorator_message(message, *args, message=reworded_message, **kwargs)
        if built_message:
          raise AssertionError(built_message)
        else:
          return False
    return wrapper
  return decorator

@tuxapp.memoize_temporarily
@tuxapp.log('Checking {}')
def check_url(url):
  try:
    from urllib.request import Request, urlopen
  except ImportError:
    from urllib2 import Request, urlopen
  try:
    return urlopen(Request(url, headers={'User-Agent': tuxapp.get_user_agent()}), timeout=10).getcode() == 200
  except: # pylint: disable=bare-except
    return False

def validate_appfile_worker(app):
  return validate_appfile(app)

@tuxapp.check('Malformed pattern')
def validate_regex(pattern):
  try:
    return bool(re.compile(pattern))
  except re.error:
    return False

check_page_contains = lambda url, string, is_case_sensitive=False: \
  bool(re.search(r'\b{}\b'.format(re.escape(re.sub(r'\s+', ' ', re.sub(r'\W+', ' ', string)))), request_url_text(url), 0 if is_case_sensitive else re.I | re.U))

check_url_http = lambda url: \
  not is_http_domain(url) or \
  tuxapp.parse_url(url).scheme == 'http'

check_url_https = lambda url: \
  tuxapp.parse_url(url).scheme == 'https' or \
  is_http_domain(url) or \
  not check_url(url.replace('http://', 'https://', 1))

get_punctuation = lambda: ('.', '!', '?')

is_http_domain = lambda url: \
  tuxapp.parse_url(url).netloc in (
    'downloads.sourceforge.net',
  )

is_library = lambda string: bool(re.match(r'^[\w.-]+\.so\b[\w.]*$', string))

is_url_valid = lambda url: \
  not re.search(r'\s', url) and \
  tuxapp.parse_url(url).scheme in ('http', 'https') and \
  bool(tuxapp.parse_url(url).netloc)

request_url_text = \
  tuxapp.memoize_temporarily(
    lambda url: re.sub(r'\s+', ' ', re.sub(r'\W+', ' ', re.sub(r'&[\w#]+;', ' ', re.sub(r'<(?!meta)[^>]+>', ' ', tuxapp.request_url(url)))))
  )

validate_app = lambda app: \
  validate_text(app) and \
  tuxapp.check('Invalid character')(lambda: bool(re.match(r'[a-z0-9-]*$', app)))() and \
  tuxapp.check('Edge dash')(lambda: not app.startswith('-') and not app.endswith('-'))() and \
  tuxapp.check('Continuous dashes')(lambda: not re.search(r'-{2}', app))() and \
  tuxapp.check('Reserved identifier')(lambda: app not in (tuxapp.get_name(),) + testing.get_distributions())

validate_app_description = lambda app, description: \
  not description or \
  validate_text(description) and \
  validate_capitalization(description) and \
  validate_terminal_punctuation(description) and \
  validate_app_homepage_containing(app, description)

validate_app_download_url = lambda app, architecture, urls: \
  architecture != 'x86-64' and not urls or \
  validate_text(urls) and \
  tuxapp.check('Duplicated item')(lambda: sorted(set(urls.split())) == sorted(urls.split()))() and \
  tuxapp.check('Contains the version number')(lambda: all(tuxapp.request_app_version(app) not in url for url in urls.split()))() and \
  all(validate_url(tuxapp.filter_app_download_url(app, url)) for url in urls.split())

validate_app_homepage_containing = \
  tuxapp.check('Not found on the homepage')(
    lambda app, string, is_case_sensitive=False: \
      string.startswith('~') or \
      check_page_contains(tuxapp.query_appfile(app, 'homepage-url'), string, is_case_sensitive)
  )

validate_app_name = lambda app, name: \
  validate_text(name) and \
  validate_no_terminal_punctuation(name) and \
  validate_app_homepage_containing(app, name, True)

validate_app_packages = lambda app, packages: \
  not packages or \
  validate_text(packages) and \
  validate_multiple_value(packages) and \
  tuxapp.update_app_package_lists(app) and all(tuxapp.query_app_package_url(app, package) for package in packages.split())

validate_app_title = lambda app, title: \
  not title or \
  validate_text(title) and \
  validate_capitalization(title) and \
  validate_no_terminal_punctuation(title) and \
  validate_app_homepage_containing(app, title)

validate_app_version_regex = lambda app, pattern: \
  validate_text(pattern, True) and \
  validate_regex(pattern) and \
  tuxapp.check('No grouping parentheses')(lambda: bool(re.search(r'\((?!\?)', pattern)) and ')' in pattern)() and \
  bool(tuxapp.request_app_version(app, pattern)) and \
  tuxapp.check(lambda *args, **kwargs: 'Extraneous character in the version number: {}'.format(tuxapp.request_app_version(app, pattern)))(lambda: not re.search(r'[\s<>"&]', tuxapp.request_app_version(app, pattern)))()

validate_appfile = lambda app: \
  reword_assertion('{}: {message}')(validate_app)(app) and \
  reword_assertion('{}: {message}')(validate_appfile_keys)(app) and \
  all(reword_assertion('{}.{}: {{message}}{}'.format(app, key, ' ({})'.format(value.replace('{', '{{').replace('}', '}}')) if value else ''))(validate_appfile_item)(app, key, value) for key, value in sorted(tuxapp.parse_appfile(app).items()))

validate_appfile_item = \
  tuxapp.check('Unknown key')(
    lambda app, key, value: \
      validate_category(value) \
        if key == 'category' else \
      validate_app_description(app, value) \
        if key == 'description' else \
      validate_desktop_entry(value) \
        if key == 'desktop-entry' else \
      validate_app_download_url(app, re.sub(r'^download-(.+)-url$', r'\1', key), value) \
        if re.match(r'download-(x86-64|x86)-url$', key) else \
      validate_executable(value) \
        if key == 'executable' else \
      validate_firejail(value) \
        if key == 'firejail' else \
      validate_free_license(value) \
        if key == 'free-license' else \
      validate_group(value) \
        if key == 'group' else \
      validate_homepage_url(value) \
        if key == 'homepage-url' else \
      validate_icon_url(value) \
        if key == 'icon-url' else \
      validate_ignored_libraries(value) \
        if key == 'ignored-libraries' else \
      validate_app_name(app, value) \
        if key == 'name' else \
      validate_note(value) \
        if key == 'note' else \
      validate_package_repository(value) \
        if key == 'package-repository' else \
      validate_app_packages(app, value) \
        if key == 'packages' else \
      validate_app_title(app, value) \
        if key == 'title' else \
      validate_app_version_regex(app, value) \
        if key == 'version-regex' else \
      validate_version_url(value) \
        if key == 'version-url' else \
      None
  )

validate_appfile_keys = lambda app: \
  tuxapp.check('Extraneous line')(lambda: all('=' in line for line in tuxapp.read_appfile(app).splitlines()))() and \
  tuxapp.check('No trailing newline')(lambda: tuxapp.read_appfile(app).endswith('\n'))() and \
  tuxapp.check('Not sorted')(lambda: tuxapp.read_appfile(app).splitlines() == sorted(tuxapp.read_appfile(app).splitlines()))() and \
  tuxapp.check('Extraneous key')(lambda: set(tuxapp.parse_appfile(app)) <= set(appfile.get_keys()))() and \
  tuxapp.check('Missing key')(lambda: set(tuxapp.parse_appfile(app)) >= set(appfile.get_keys()))() and \
  tuxapp.check('Duplicated key')(lambda: sorted(tuxapp.parse_appfile(app)) == sorted(line.split('=', 1)[0] for line in tuxapp.read_appfile(app).splitlines()))() and \
  tuxapp.check('Unknown error')(lambda: sorted(tuxapp.parse_appfile(app).keys()) == sorted(appfile.get_keys()))()

validate_appfiles = lambda apps: utilities.call_parallel(validate_appfile_worker, apps)

validate_boolean = lambda string: \
  validate_single_value(string) and \
  tuxapp.check('Unsupported value')(lambda: string in ('no', 'yes'))()

validate_capitalization = \
  tuxapp.check('Not capitalized')(
    lambda string: string[0] == string[0].upper()
  )

validate_category = lambda category: \
  validate_text(category) and \
  validate_single_value(category) and \
  tuxapp.check('Unknown category')(lambda: category in appfile.get_categories())()

validate_command = \
  tuxapp.check('Failed to parse')(
    lambda command: bool(tuxapp.split_command(command))
  )

validate_desktop_entry = lambda string: \
  not string or \
  validate_text(string) and \
  tuxapp.check('Extraneous key')(lambda: all('=' in line for line in string.split('\\n')))() and \
  tuxapp.check('Duplicated key')(lambda keys: sorted(set(keys)) == sorted(keys))(tuple(line.split('=', 1)[0] for line in string.split('\\n'))) and \
  tuxapp.check('Unsupported key')(lambda: all(line.split('=', 1)[0] in ('Terminal',) for line in string.split('\\n')))() and \
  all(validate_text(string) for line in string.split('\\n') for string in line.split('=', 1)) and \
  all(validate_desktop_entry_value(line.split('=', 1)[0], line.split('=', 1)[1]) for line in string.split('\\n'))

validate_desktop_entry_value = lambda key, value: \
  tuxapp.check('Wrong value for key {}'.format(key))(lambda value: value in ('false', 'true'))(value) \
    if key == 'Terminal' else \
  True

validate_executable = lambda command: \
  validate_text(command) and \
  validate_command(command) and \
  tuxapp.check('Does not contain ./')(lambda: './' in command)()

validate_firejail = lambda options: \
  not options or \
  validate_text(options) and \
  validate_command(options)

validate_free_license = lambda string: \
  validate_text(string) and \
  validate_boolean(string)

validate_group = lambda group, is_permissive=False: \
  validate_text(group) and \
  validate_single_value(group) and \
  (is_permissive or tuxapp.check('Unknown group')(lambda: group in appfile.get_groups())())

validate_homepage_url = lambda url: validate_url(url)

validate_icon_url = lambda url: validate_url(url)

validate_ignored_libraries = lambda libraries: \
  not libraries or \
  validate_text(libraries) and \
  validate_multiple_value(libraries) and \
  tuxapp.check('Invalid name')(all)(is_library(library) for library in libraries.split())

validate_multiple_value = lambda string: \
  tuxapp.check('Not sorted')(lambda string: string.split() == sorted(string.split()))(string) and \
  tuxapp.check('Duplicated item')(lambda: sorted(set(string.split())) == sorted(string.split()))()

validate_no_terminal_punctuation = \
  tuxapp.check('Terminal punctuation')(
    lambda string: string[-1] not in get_punctuation()
  )

validate_note = lambda note: \
  not note or \
  validate_text(note) and \
  validate_capitalization(note) and \
  validate_terminal_punctuation(note)

validate_package_repository = lambda repository: \
  validate_text(repository) and \
  validate_single_value(repository) and \
  tuxapp.check('Unknown repository')(lambda: repository in appfile.get_package_repositories())()

validate_single_value = \
  tuxapp.check('Not a single value')(
    lambda string: len(string.split()) == 1
  )

validate_terminal_punctuation = \
  tuxapp.check('No terminal punctuation')(
    lambda string: string[-1] in get_punctuation()
  )

validate_text = lambda string, is_whitespacy=False: \
  tuxapp.check('Is required')(lambda string: bool(string))(string) and \
  tuxapp.check('Tab character')(lambda string: '\t' not in string)(string) and \
  tuxapp.check('Edge whitespace')(lambda string, is_whitespacy: is_whitespacy or not re.search(r'^\s', string) and not re.search(r'\s$', string))(string, is_whitespacy) and \
  tuxapp.check('Continuous whitespace')(lambda string, is_whitespacy: is_whitespacy or not re.search(r'\s{2}', string))(string, is_whitespacy)

validate_url = lambda url: \
  validate_text(url) and \
  tuxapp.check('Invalid URL')(lambda: is_url_valid(url))() and \
  tuxapp.check('No path')(lambda: bool(tuxapp.parse_url(url).path))() and \
  tuxapp.check('Contains a fragment')(lambda: not tuxapp.parse_url(url).fragment)() and \
  tuxapp.check('Failed to request URL')(lambda: check_url(url))() and \
  tuxapp.check('Accessible by HTTPS')(lambda: check_url_https(url))() and \
  tuxapp.check('Only accessible by HTTP')(lambda: check_url_http(url))()

validate_version_url = lambda url: \
  validate_url(url) and \
  tuxapp.check('Does not end with /latest')(lambda: not re.search(r'{}/releases$'.format(utilities.get_github_url_pattern()), url))()
