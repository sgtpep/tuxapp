# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import collections
import glob
import os
import re
import time

from lib import (
  generating,
  tuxapp,
  utilities,
  validation,
)

try:
  from html.parser import HTMLParser
except ImportError:
  from HTMLParser import HTMLParser
# pylint: disable=abstract-method
class BaseParser(HTMLParser):
  content = ''
  content_attributes = {}
  content_tag = None
  is_head = False
  is_multiple = False
  previous_attributes = {}
  previous_tag = None
  results = []
  schema_org_data_type = None

  data_types = (
    'Product',
    'SoftwareApplication',
    'WebSite',
  )

  def __init__(self, *args, **kwargs):
    HTMLParser.__init__(self, *args, **kwargs)
    self.results = []

  def add_result(self, result):
    self.results.append(self.filter_result(result) if self.is_multiple else (result[:-1], self.filter_result(result[-1])))

  def feed(self, *args, **kwargs):
    HTMLParser.feed(self, *args, **kwargs)
    self.raise_result()

  def filter_result(self, string):
    return re.sub(r'\s+', ' ', string.replace('\t', ' ')).strip()

  def handle_data(self, data):
    getattr(self, 'on_data', lambda *args, **kwargs: None)(self.previous_tag, self.previous_attributes, data.strip())
    if self.content_tag:
      self.content += data
    if self.previous_attributes.get('itemprop'):
      getattr(self, 'on_schema_org', lambda *args, **kwargs: None)(self.schema_org_data_type, data, self.previous_tag, self.previous_attributes)
    if self.previous_tag == 'script' and self.previous_attributes.get('type') == 'application/ld+json' and data.strip():
      import json
      decoded_data = json.loads(data)
      items = decoded_data if isinstance(decoded_data, list) else [decoded_data]
      for item in items:
        if '@type' in item:
          getattr(self, 'on_json_ld', lambda *args, **kwargs: None)(item)

  def handle_endtag(self, tag):
    if tag == self.content_tag:
      getattr(self, 'on_content', lambda *args, **kwargs: None)(self.content_tag, self.content_attributes, self.content.strip())
      self.content = ''
      self.content_attributes = {}
      self.content_tag = None
    if self.is_head and tag == 'head':
      self.raise_result()

  def handle_starttag(self, tag, attributes):
    attributes = dict(attributes)
    getattr(self, 'on_tag', lambda *args, **kwargs: None)(tag, attributes)
    if attributes.get('itemtype'):
      self.schema_org_data_type = attributes['itemtype'].rsplit('/', 1)[-1]
    if tag == 'meta' and attributes.get('content') and attributes.get('itemprop'):
      getattr(self, 'on_schema_org', lambda *args, **kwargs: None)(self.schema_org_data_type, attributes['content'], tag, attributes)
    self.previous_attributes = attributes
    self.previous_tag = tag

  def raise_result(self):
    if self.is_multiple:
      raise ResultException(self.results)
    else:
      raise ResultException(sorted(self.results, key=lambda item: item[:-1], reverse=True)[0][-1] if self.results else '')

  def read_content(self, tag, attributes):
    self.content_attributes = attributes
    self.content_tag = tag

class BaseURLParser(BaseParser):
  def on_tag(self, tag, attributes):
    if tag == 'base' and attributes.get('href'):
      raise ResultException(attributes['href'])

class ChangelogURLParser(BaseParser):
  priority = (
    'anchor',
    'schema-org',
    'json-ld',
  )

  def on_content(self, tag, attributes, content):
    if tag == 'a' and attributes.get('href') and re.match(r'(changelog|release\s+notes|what[^\s]+s\s+new)\b', content, re.I | re.S):
      self.add_result((self.priority.index('anchor'), attributes['href']))

  def on_json_ld(self, item):
    if item.get('releaseNotes'):
      self.add_result((self.priority.index('json-ld'), item['releaseNotes']))

  def on_schema_org(self, data_type, content, tag, attributes):
    if attributes['itemprop'] == 'releaseNotes':
      self.add_result((self.priority.index('schema-org'), content))

  def on_tag(self, tag, attributes):
    if tag == 'a':
      self.read_content(tag, attributes)

class DescriptionParser(BaseParser):
  priority = (
    'description',
    'og-description',
    'schema-org-WebSite',
    'json-ld-WebSite',
    'schema-org-Product',
    'json-ld-Product',
    'schema-org-SoftwareApplication',
    'json-ld-SoftwareApplication',
  )

  def on_json_ld(self, item):
    if item['@type'] in self.data_types and item.get('description'):
      self.add_result((self.priority.index('json-ld-{}'.format(item['@type'])), item['description']))

  def on_schema_org(self, data_type, content, tag, attributes):
    if data_type in self.data_types and attributes['itemprop'] == 'description':
      self.add_result((self.priority.index('schema-org-{}'.format(data_type)), content))

  def on_tag(self, tag, attributes):
    if tag == 'meta' and attributes.get('content'):
      if attributes.get('name') == 'description':
        self.add_result((self.priority.index('description'), attributes['content']))
      elif attributes.get('property') == 'og:description':
        self.add_result((self.priority.index('og-description'), attributes['content']))

class DownloadsURLParser(BaseParser):
  priority = (
    'download',
    'downloads',
  )

  def filter_url(self, url):
    return re.sub(r'^.+({}/releases\b).*$'.format(utilities.get_github_url_pattern()), r'https://\1', url, 1)

  def on_content(self, tag, attributes, content):
    if tag == 'a' and attributes.get('href') and tuxapp.parse_url(attributes['href']).netloc not in ('itunes.apple.com', 'play.google.com'):
      if re.search(r'^(desktop\s+apps|downloads?)$|\s+(downloads|platforms)$|\bsystems\b.+\blanguages\b', content, re.I | re.S):
        self.add_result((self.priority.index('downloads'), self.filter_url(attributes['href'])))
      elif re.match(r'[Dd]ownload\s+[A-Z]', content, re.S) and not content.endswith(' ZIP'):
        self.add_result((self.priority.index('download'), self.filter_url(attributes['href'])))

  def on_tag(self, tag, attributes):
    if tag == 'a':
      self.read_content(tag, attributes)

class GitHubNameParser(BaseParser):
  is_article = False

  def on_content(self, tag, attributes, content):
    if tag == 'h1':
      raise ResultException(content.split(' - ', 1)[0])

  def on_tag(self, tag, attributes):
    if tag == 'article':
      self.is_article = True
    elif tag == 'h1' and self.is_article:
      self.read_content(tag, attributes)

class GitHubScreenshotURLsParser(BaseParser):
  is_article = False
  is_multiple = True
  paragraph_number = 0

  def on_tag(self, tag, attributes):
    if tag == 'article':
      self.is_article = True
    elif tag == 'p' and self.is_article:
      self.paragraph_number += 1
    elif tag == 'img' and attributes.get('src') and self.previous_tag == 'a' and self.previous_attributes.get('href') and (is_image_url(self.previous_attributes['href']) or self.previous_attributes['href'] == attributes['src'] or is_image_url(attributes.get('data-canonical-src', '')) and self.previous_attributes['href'] == attributes['src']) and self.is_article and self.paragraph_number > 1:
      self.add_result(attributes['src'])

class IconURLParser(BaseParser):
  is_head = True

  rels = (
    'shortcut icon',
    'apple-touch-icon',
    'apple-touch-icon-precomposed',
    'icon',
  )

  def on_tag(self, tag, attributes):
    if tag == 'link' and attributes.get('href') and attributes.get('rel') in self.rels:
      self.add_result((
        int(attributes.get('sizes', '0x0').split('x', 1)[0]),
        self.rels.index(attributes['rel']),
        attributes['href'],
      ))

class ImageURLParser(BaseParser):
  priority = (
    'og-image',
    'schema-org',
    'json-ld',
  )

  def on_json_ld(self, item):
    if item['@type'] in self.data_types and item.get('image'):
      self.add_result((self.priority.index('json-ld'), item['image']))

  def on_schema_org(self, data_type, content, tag, attributes):
    if data_type in self.data_types and attributes['itemprop'] == 'image':
      self.add_result((self.priority.index('schema-org'), content))

  def on_tag(self, tag, attributes):
    if tag == 'meta' and attributes.get('property') in ('og:image', 'og:image:url', 'og:image:secure-url') and attributes.get('content'):
      self.add_result((self.priority.index('og-image'), attributes['content']))

class NameParser(BaseParser):
  priority = (
    'heading-anchor',
    'og-site-name',
    'schema-org-WebSite',
    'json-ld-WebSite',
    'schema-org-Product',
    'json-ld-Product',
    'schema-org-SoftwareApplication',
    'json-ld-SoftwareApplication',
    'application-name',
  )

  def on_content(self, tag, attributes, content):
    if tag in ('a', 'h1'):
      self.add_result((self.priority.index('heading-anchor'), content))

  def on_json_ld(self, item):
    if item['@type'] in self.data_types and item.get('name'):
      self.add_result((self.priority.index('json-ld-{}'.format(item['@type'])), item['name']))

  def on_schema_org(self, data_type, content, tag, attributes):
    if data_type in self.data_types and attributes['itemprop'] == 'name':
      self.add_result((self.priority.index('schema-org-{}'.format(data_type)), content))

  def on_tag(self, tag, attributes):
    if tag == 'a' and self.previous_tag == 'h1' or tag == 'h1' and self.previous_tag == 'a':
      self.read_content(tag, attributes)
    elif tag == 'meta' and attributes.get('content'):
      if attributes.get('name') == 'application-name':
        self.add_result((self.priority.index('application-name'), attributes['content']))
      elif attributes.get('property') == 'og:site_name':
        self.add_result((self.priority.index('og-site-name'), attributes['content']))

class ResultException(Exception):
  pass

class ScreenshotURLsParser(BaseParser):
  is_multiple = True
  tag = None

  def on_tag(self, tag, attributes):
    if tag in ('a', 'img') and re.search(r'\bscreen', str(attributes), re.I):
      if tag == 'a' and attributes.get('href') and is_image_url(attributes['href']) and '/File:' not in attributes['href'] and (not self.tag or self.tag == tag):
        self.tag = tag
        self.add_result(attributes['href'])
      elif tag == 'img' and (not self.tag or self.tag == tag):
        self.tag = tag
        if attributes.get('srcset'):
          self.add_result(attributes['srcset'].split()[0])
        elif attributes.get('src'):
          self.add_result(attributes['src'])

class ScreenshotsURLParser(BaseParser):
  def on_content(self, tag, attributes, content):
    if tag == 'a' and attributes.get('href') and re.search(r'\bscreenshots\b', content, re.I):
      raise ResultException(attributes['href'])

  def on_tag(self, tag, attributes):
    if tag == 'a':
      if attributes.get('href') and re.search(r'\bscreenshots\b', attributes['href'], re.I):
        raise ResultException(attributes['href'])
      else:
        self.read_content(tag, attributes)

class TitleParser(BaseParser):
  is_head = True

  priority = (
    'title',
    'og-title',
  )

  def on_data(self, tag, attributes, data):
    if tag == 'title':
      self.add_result((self.priority.index('title'), data))

  def on_tag(self, tag, attributes):
    if tag == 'meta' and attributes.get('property') == 'og:title' and attributes.get('content'):
      self.add_result((self.priority.index('og-title'), attributes['content']))

class VideoPosterURLsParser(BaseParser):
  is_multiple = True

  def on_tag(self, tag, attributes):
    if (tag == 'source' and self.previous_tag in ('source', 'video') or tag == 'video') and attributes.get('src') and os.path.splitext(tuxapp.parse_url(attributes['src']).path)[1] == '.mp4':
      self.add_result((attributes if tag == 'video' else self.previous_attributes).get('poster', ''))

class VideoURLsParser(BaseParser):
  is_multiple = True

  def on_tag(self, tag, attributes):
    if (tag == 'source' and self.previous_tag in ('source', 'video') or tag == 'video') and attributes.get('src') and os.path.splitext(tuxapp.parse_url(attributes['src']).path)[1] == '.mp4':
      self.add_result(attributes['src'])

def parse_app_worker(app):
  return parse_app(app)

def parse_html(parser, html):
  try:
    parser().feed(html)
  except ResultException as exception:
    return exception.args[0] if exception.args else ''

check_github_releases = lambda repository: \
  repository \
    if repository and not re.search(r'/releases$', request_url_headers_cached(utilities.build_github_url(repository, 'releases/latest')), re.M) else \
  ''

check_url_name = lambda url, name: \
  name.title() \
    if validation.check_page_contains(url, name.title(), True) else \
  ''

download_missing_app_file = lambda url, pattern: \
  next(glob.iglob(pattern), None) or \
  tuxapp.rename_file(tuxapp.download_missing_app_file(tuxapp.get_name(), url, os.path.splitext(pattern)[0]), '{}.{}'.format(os.path.splitext(pattern)[0], utilities.detect_image_extension(os.path.splitext(pattern)[0])))

extract_url_name = lambda url: re.sub(r'-+', ' ', re.sub(r'^www\.', '', tuxapp.parse_url(url).netloc).split('.', 1)[0])

filter_app_downloads_url = lambda app, url: \
  '' \
    if re.search({
      'firefox-developer-edition': r'/firefox/',
      'google-chrome-beta': r'/chrome/browser/$',
      'nylas-mail': r'\.youtube\.com/',
      'thunderbird': r'/firefox/',
    }.get(app, r'^$'), url) else \
  url

filter_app_screenshot_url = lambda app, url: \
  '' \
    if re.search({
      'avidemux': r'/menu-screenshots-inactive\.png$',
      'inboxer': r'\.(githubusercontent\.com|shields\.io)/',
      'jumpfm': r'/dev\.png$',
      'mailspring': r'/(ic-|send-later@)',
      'pencil': r'/(000/010/630|000/010/632)/large\.png$',
      'qupzilla': r'/(other|win(|xp))_',
      'rambox': r'/icons/',
      'skype': r'/screenshots\.debian\.net/',
      'visual-studio-code': r'\.svg$',
    }.get(app, r'^$'), url) else \
  url

filter_app_screenshot_urls = lambda app, urls: tuple(url for url in (filter_app_screenshot_url(app, url) for url in urls) if url)

filter_app_video_url = lambda app, url, reference_url=None: \
  '' \
    if re.search({
      'emercoin': r'=HdmfJLa6iRg$',
      'fman': r'/rocket\.mp4',
    }.get(app, r'^$'), reference_url or url) or is_github_repository_url(tuxapp.query_appfile(app, 'homepage-url')) else \
  re.sub(r'\.pagespeed\.ce\..+$', '', url) \
    if app == 'fman' else \
  url

filter_app_video_urls = lambda app, urls, reference_urls=None: tuple(url for url in (filter_app_video_url(app, url, reference_url) for url, reference_url in zip(urls, reference_urls or urls)) if url)

filter_github_repository = lambda repository: \
  '' \
    if repository in (
      'DuckieTV/Nightlies',
      'mozilla/bedrock',
    ) else \
  repository

filter_unique = lambda items, reference_items=None: tuple(collections.OrderedDict((reference_item, item) for reference_item, item in zip(reference_items or items, items)).values())

filter_url_accessibility = lambda url: \
  url \
    if url and validation.check_url(url) else \
  ''

get_debian_screenshots_url = lambda package: 'https://screenshots.debian.net/package/{}'.format(package)

is_github_repository_url = lambda url: bool(re.search('{}$'.format(utilities.get_github_url_pattern()), url))

is_github_url = lambda url: bool(re.search(utilities.get_github_url_pattern(), url))

is_image_url = lambda url: \
  os.path.splitext(tuxapp.parse_url(url).path)[1].lower() in (
    '.gif',
    '.jpeg',
    '.jpg',
    '.png',
    '.svg',
  )

normalize_url = lambda page_url, url, base_url=None: \
  url \
    if re.match(r'https?://', url) else \
  '{}:{}'.format(tuxapp.parse_url(page_url).scheme, url) \
    if url.startswith('//') else \
  '{0.scheme}://{0.netloc}{1}'.format(tuxapp.parse_url(page_url), url) \
    if url.startswith('/') else \
  '{0.scheme}://{0.netloc}{1}{2}'.format(tuxapp.parse_url(base_url or parse_base_url(page_url)), os.path.normpath(os.path.join(os.path.dirname(tuxapp.parse_url(base_url or parse_base_url(page_url)).path or '/'), url)), '/' if url and url[-1] == '/' else '') \
    if url and url != '#' and not re.match(r'\w+:', url) else \
  ''

parse_app = lambda app: \
  update_app_data(app) and \
  update_app_data_files(app)

parse_app_changelog_url = lambda app, url: \
  parse_changelog_url(url) or \
  parse_app_downloads_url(app, url) and parse_changelog_url(parse_app_downloads_url(app, url)) or \
  parse_github_releases_url(url)

parse_app_debian_screenshot_urls = lambda app: tuple(normalize_url(get_debian_screenshots_url(app), screenshot_url) for screenshot_url in parse_screenshot_urls(get_debian_screenshots_url(app)) if os.path.basename(tuxapp.parse_url(screenshot_url).path) != 'no-screenshots-available.svg')

parse_app_download_formats = lambda app, url: ' '.join(sorted(set(format.lower() for format in re.findall(r'\b(appimage|deb|flatpak|rpm|snap|tar)\b', request_url_cached(parse_app_download_formats_url(app, url)), re.I))))

parse_app_download_formats_url = lambda app, url: \
  parse_github_latest_release_url(url) or \
  parse_app_downloads_url(app, url) or \
  url

parse_app_downloads_url = lambda app, url: \
  filter_app_downloads_url(app, parse_downloads_url(url)) or \
  parse_github_latest_release_url(url)

parse_app_screenshot_urls = lambda app, url: \
  filter_app_screenshot_urls(app, parse_github_screenshot_urls(url)) \
    if is_github_repository_url(url) else \
  (filter_app_screenshot_urls(app, parse_screenshot_urls(parse_screenshots_url(url) or url)) or (filter_app_screenshot_urls(app, parse_github_screenshot_urls(utilities.build_github_url(parse_github_repository(url)))) if parse_github_repository(url) else ())) + \
  filter_app_screenshot_urls(app, parse_app_debian_screenshot_urls(app))

parse_app_video_thumbnail_urls = lambda app, url: \
  filter_app_video_urls(app, parse_youtube_thumbnail_urls(url), parse_youtube_urls(url)) + \
  filter_app_video_urls(app, parse_video_poster_urls(url), parse_video_src_urls(url))

parse_app_video_urls = lambda app, url: \
  filter_app_video_urls(app, parse_youtube_urls(url)) + \
  filter_app_video_urls(app, parse_video_src_urls(url))

parse_apps = lambda apps: utilities.call_parallel(parse_app_worker, apps)

parse_base_url = lambda url: normalize_url(url, parse_html(BaseURLParser, request_url_cached(url)) or url, url)

parse_changelog_url = lambda url: normalize_url(url, parse_html(ChangelogURLParser, request_url_cached(url)))

parse_description = lambda url: \
  '' \
    if is_github_repository_url(url) else \
  parse_html(DescriptionParser, request_url_cached(url))

parse_downloads_url = lambda url: normalize_url(url, parse_html(DownloadsURLParser, request_url_cached(url)))

parse_github_latest_release_url = lambda url: utilities.build_github_url(check_github_releases(parse_github_repository(url)), 'releases/latest')

parse_github_releases_url = lambda url: utilities.build_github_url(check_github_releases(parse_github_repository(url)), 'releases')

parse_github_repository = lambda url: \
  is_github_repository_url(url) and tuxapp.search(utilities.get_github_url_pattern(), url, 0, 1) or \
  filter_github_repository(tuxapp.search(r'{}/releases\b'.format(utilities.get_github_url_pattern()), request_url_cached(url), 0, 1)) or \
  filter_github_repository(tuxapp.search(utilities.get_github_url_pattern(), request_url_cached(url), 0, 1))

parse_github_screenshot_urls = lambda url: tuple(normalize_url(url, screenshot_url) for screenshot_url in parse_html(GitHubScreenshotURLsParser, request_url_cached(url)))

parse_icon_url = lambda url: \
  '' \
    if is_github_url(url) else \
  filter_url_accessibility(normalize_url(url, parse_html(IconURLParser, request_url_cached(url)) or '/favicon.ico'))

parse_image_url = lambda url: \
  '' \
    if is_github_url(url) else \
  filter_url_accessibility(normalize_url(url, parse_html(ImageURLParser, request_url_cached(url))))

parse_name = lambda url: \
  check_url_name(url, tuxapp.parse_url(url).path.lstrip('/').split('/', 1)[0]) \
    if tuxapp.parse_url(url).netloc.endswith('.github.io') and tuxapp.parse_url(url).path.lstrip('/') else \
  parse_html(GitHubNameParser, request_url_cached(url)) or \
  check_url_name(url, tuxapp.parse_url(url).path.split('/')[-1]) \
    if is_github_repository_url(url) else \
  parse_html(NameParser, request_url_cached(url)) or \
  check_url_name(url, extract_url_name(url))

parse_screenshot_urls = lambda url: tuple(normalize_url(url, screenshot_url) for screenshot_url in parse_html(ScreenshotURLsParser, request_url_cached(url)))

parse_screenshots_url = lambda url: normalize_url(url, parse_html(ScreenshotsURLParser, request_url_cached(url)))

parse_title = lambda url: \
  re.sub(r'^.+ - ', '', parse_html(DescriptionParser, request_url_cached(url))) \
    if is_github_repository_url(url) else \
  parse_html(TitleParser, request_url_cached(url))

parse_version_url = lambda url: \
  '{}/releases/latest'.format(url) \
    if is_github_repository_url(url) else \
  parse_github_latest_release_url(url) \
    if parse_github_repository(url) else \
  ''

parse_video_poster_urls = lambda url: tuple(normalize_url(url, poster_url) or '-' for video_url, poster_url in zip(parse_html(VideoURLsParser, request_url_cached(url)), parse_html(VideoPosterURLsParser, request_url_cached(url))))

parse_video_src_urls = lambda url: tuple(normalize_url(url, video_url) for video_url in parse_html(VideoURLsParser, request_url_cached(url)))

parse_youtube_ids = lambda url: tuple(set(re.findall(r'\b(?:youtu\.be/|youtube\.com/(?:(?:embed|v)/|watch\?v=))([\w-]+)', request_url_cached(url))))

parse_youtube_thumbnail_urls = lambda url: tuple('https://img.youtube.com/vi/{}/hqdefault.jpg'.format(id) for id in parse_youtube_ids(url))

parse_youtube_urls = lambda url: tuple('https://www.youtube.com/watch?v={}'.format(id) for id in parse_youtube_ids(url))

request_url_cached = \
  tuxapp.memoize(
    lambda url: tuxapp.request_url(url)
  )

request_url_headers_cached = \
  tuxapp.memoize(
    lambda url: tuxapp.request_url_headers(url)
  )

update_app_data = lambda app: \
  update_app_version_data(app) and \
  utilities.update_data_items((
    ((app, 'changelog-url'), parse_app_changelog_url(app, tuxapp.query_appfile(app, 'homepage-url'))),
    ((app, 'download-formats'), parse_app_download_formats(app, tuxapp.query_appfile(app, 'homepage-url'))),
    ((app, 'downloads-url'), parse_app_downloads_url(app, tuxapp.query_appfile(app, 'homepage-url'))),
    ((app, 'github-repository'), parse_github_repository(tuxapp.query_appfile(app, 'homepage-url'))),
    ((app, 'image-url'), parse_image_url(tuxapp.query_appfile(app, 'homepage-url'))),
    ((app, 'screenshot-urls'), ' '.join(filter_unique(parse_app_screenshot_urls(app, tuxapp.query_appfile(app, 'homepage-url'))))),
    ((app, 'video-thumbnail-urls'), ' '.join(filter_unique(parse_app_video_thumbnail_urls(app, tuxapp.query_appfile(app, 'homepage-url')), parse_app_video_urls(app, tuxapp.query_appfile(app, 'homepage-url'))))),
    ((app, 'video-urls'), ' '.join(filter_unique(parse_app_video_urls(app, tuxapp.query_appfile(app, 'homepage-url'))))),
  ))

update_app_data_files = lambda app: \
  update_app_file(app, generating.get_app_icon_pattern, tuxapp.query_appfile(app, 'icon-url')) and \
  update_app_file(app, generating.get_app_image_pattern, utilities.query_data((app, 'image-url'))) and \
  update_app_files(app, generating.get_app_screenshot_pattern, utilities.query_data((app, 'screenshot-urls')).split()) and \
  update_app_files(app, generating.get_app_video_thumbnail_pattern, tuple(url for url in utilities.query_data((app, 'video-thumbnail-urls')).split() if url != '-'))

update_app_file = lambda app, get_pattern, url: update_app_files(app, get_pattern, (url,) if url else ())

update_app_files = lambda app, get_pattern, urls: \
  all(tuxapp.remove_file(path) for path in glob.iglob(get_pattern(app)) if os.path.splitext(path)[0] not in tuple(os.path.splitext(get_pattern(app, url))[0] for url in urls)) and \
  all(download_missing_app_file(url, get_pattern(app, url)) for url in urls)

update_app_version_data = lambda app: \
  True \
    if utilities.query_data((app, 'version')) == tuxapp.request_app_version(app) else \
  utilities.update_data_items((
    ((app, 'timestamp'), int(time.time())),
    ((app, 'version'), tuxapp.request_app_version(app)),
  ))
