import imp
import os
import re

try:
  from html.parser import HTMLParser
except ImportError:
  from HTMLParser import HTMLParser

tuxapp = imp.load_source('tuxapp', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tuxapp'))
validate = imp.load_source('validate', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'validate'))

class BaseParser(HTMLParser):
  contents = ''
  contents_tag = None
  is_head = False
  parent_attributes = {}
  parent_tag = None

  data_types = (
    'Product',
    'SoftwareApplication',
    'WebSite',
  )

  def __init__(self, *args, **kwargs):
    HTMLParser.__init__(self, *args, **kwargs)
    self.results = []

  def add_result(self, result):
    self.results.append(result)

  def feed(self, *args, **kwargs):
    HTMLParser.feed(self, *args, **kwargs)
    self.raise_result()

  def handle_data(self, data):
    if self.contents_tag:
      self.contents += data
    if self.parent_tag == 'script' and self.parent_attributes.get('type') == 'application/ld+json':
      import json
      data = json.loads(data)
      items = data if isinstance(data, list) else [data]
      for item in items:
        if item.get('@type') in self.data_types:
          getattr(self, 'on_json_ld', lambda *args, **kwargs: None)(item)

  def handle_endtag(self, tag):
    getattr(self, 'on_tag_end', lambda *args, **kwargs: None)(tag)
    if tag == self.contents_tag:
      getattr(self, 'on_contents', lambda *args, **kwargs: None)(tag, self.contents)
      self.contents_tag = None
    if self.is_head and tag == 'head':
      self.raise_result()
    self.parent_attributes = {}
    self.parent_tag = None

  def handle_starttag(self, tag, attributes):
    attributes = dict(attributes)
    getattr(self, 'on_tag_start', lambda *args, **kwargs: None)(tag, attributes)
    if tag == 'meta' and attributes.get('content') and self.parent_attributes.get('itemtype', '').startswith("http://schema.org/"):
      type = self.parent_attributes['itemtype'].rsplit('/', 1)[-1]
      if type in self.data_types:
        getattr(self, 'on_schema_org', lambda *args, **kwargs: None)(type, attributes)
    self.parent_attributes = attributes
    self.parent_tag = tag

  def raise_result(self):
    if self.results:
      raise ResultException(sorted(self.results)[-1][-1])

  def read_contents(self, tag):
    self.contents_tag = tag

class BaseURLParser(BaseParser):
  def on_tag_start(self, tag, attributes):
    if tag == 'base' and attributes.get('href'):
      raise ResultException(attributes['href'])

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
    if item.get('description'):
      self.add_result((self.priority.index('json-ld-{}'.format(item['@type'])), item['description']))

  def on_schema_org(self, type, attributes):
    if attributes.get('itemprop') == 'description':
      self.add_result((self.priority.index('schema-org-{}'.format(type)), attributes['content']))

  def on_tag_start(self, tag, attributes):
    if tag == 'meta' and attributes.get('content'):
      if attributes.get('name') == 'description':
        self.add_result((self.priority.index('description'), attributes['content']))
      elif attributes.get('property') == 'og:description':
        self.add_result((self.priority.index('og-description'), attributes['content']))

class IconURLParser(BaseParser):
  is_head = True

  rels = (
    "shortcut icon",
    'apple-touch-icon',
    'apple-touch-icon-precomposed',
    'icon',
  )

  def on_tag_start(self, tag, attributes):
    if tag == 'link' and attributes.get('href') and attributes.get('rel') in self.rels:
      self.add_result((
        int(attributes.get('sizes', "0x0").split('x', 1)[0]),
        self.rels.index(attributes['rel']),
        attributes['href'],
      ))

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

  def on_contents(self, tag, contents):
    if tag in ('a', 'h1'):
      self.add_result((self.priority.index('heading-anchor'), contents))

  def on_json_ld(self, item):
    if item.get('name'):
      self.add_result((self.priority.index('json-ld-{}'.format(item['@type'])), item['name']))

  def on_schema_org(self, type, attributes):
    if attributes.get('itemprop') == 'name':
      self.add_result((self.priority.index('schema-org-{}'.format(type)), attributes['content']))

  def on_tag_start(self, tag, attributes):
    if tag == 'a' and self.parent_tag == 'h1' or tag == 'h1' and self.parent_tag == 'a':
      self.read_contents(tag)
    elif tag == 'meta' and attributes.get('content'):
      if attributes.get('name') == 'application-name':
        self.add_result((self.priority.index('application-name'), attributes['content']))
      elif attributes.get('property') == 'og:site_name':
        self.add_result((self.priority.index('og-site-name'), attributes['content']))

class ResultException(Exception):
  pass

class TitleParser(BaseParser):
  is_head = True

  priority = (
    'title',
    'og-title',
  )

  def on_contents(self, tag, contents):
    if tag == 'title':
      self.add_result((self.priority.index('title'), contents))

  def on_tag_start(self, tag, attributes):
    if tag == 'meta' and attributes.get('property') == 'og:title' and attributes.get('content'):
      self.add_result((self.priority.index('og-title'), attributes['content']))
    elif tag == 'title':
      self.read_contents(tag)

def parse_html(parser, html):
  try:
    parser().feed(html)
  except ResultException as exception:
    if exception.args and tuxapp.is_string(exception.args[0]):
      return re.sub(r"\s+", ' ', exception.args[0].strip())

extract_url_name = lambda url: re.sub(r"-+", ' ', re.sub(r"^www\.", '', tuxapp.parse_url(url).netloc).split('.', 1)[0]).title()

fetch_url = tuxapp.memoizes()(
  lambda *args, **kwargs: tuxapp.fetch_url(*args, **kwargs)
)

filter_name = lambda url, name: name if validate.is_on_page(url, name, True) else None

normalize_url = lambda page_url, url, base_url=None: \
  url \
    if re.match(r"^https?://", url) else \
  "{}:{}".format(tuxapp.parse_url(page_url).scheme, url) \
    if url.startswith("//") else \
  "{0.scheme}://{0.netloc}{1}".format(tuxapp.parse_url(page_url), normalize_url_path(url)) \
    if url.startswith('/') else \
  "{0.scheme}://{0.netloc}{1}".format(
    tuxapp.parse_url(base_url or parse_base_url(page_url)),
    normalize_url_path("/{}/{}".format(tuxapp.parse_url(base_url or parse_base_url(page_url)).path, url)),
  )

normalize_url_path = lambda path: re.sub(r"^//", '/', os.path.normpath(path))

parse_base_url = lambda url: normalize_url(url, parse_html(BaseURLParser, fetch_url(url)) or url, url)

parse_description = lambda url: parse_html(DescriptionParser, fetch_url(url))

parse_icon_url = lambda url: normalize_url(url, parse_html(IconURLParser, fetch_url(url)) or "/favicon.ico")

parse_name = lambda url: \
  filter_name(url, tuxapp.parse_url(url).path.lstrip('/').split('/', 1)[0]) \
    if ".github.io/" in url and tuxapp.parse_url(url).path.lstrip('/') else \
  parse_html(NameParser, fetch_url(url)) or filter_name(url, extract_url_name(url))

parse_title = lambda url: parse_html(TitleParser, fetch_url(url))
