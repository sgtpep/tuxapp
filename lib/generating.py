# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import collections
import datetime
import functools
import glob
import os
import re
import time

from lib import (
  tuxapp,
  utilities,
  validation,
)

def build_data_uri(path, width=None):
  import base64
  import mimetypes
  return 'data:{};base64,{}'.format(mimetypes.guess_type('_.{}'.format(utilities.detect_image_extension(path)))[0], base64.b64encode(resize_image(path, width) if width and utilities.detect_image_extension(path) != 'svg' else tuxapp.read_file_binary(path))) \

def build_json(value):
  import json
  return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True)

def escape_html(string):
  try:
    import html
    return html.escape(string)
  except ImportError:
    import cgi
    return cgi.escape(string, True) # pylint: disable=deprecated-method

def generate_app_page_worker(app):
  return generate_app_page(app)

def read_added_apps(size):
  lines = tuxapp.read_process_lines(r'''
  git -C {} log --name-status --pretty=format:%ct ./apps | \
  grep -Po '(^\d+|(?<=^A\tapps/)[^.].+)' | \
  head -100
  '''.format(tuxapp.quote_argument(tuxapp.get_project_path())))
  result = []
  timestamp = int(time.time())
  for line in lines:
    if line.isdigit() and len(line) >= 10:
      timestamp = int(line)
    elif os.path.isfile(tuxapp.get_appfile_path(line)) and all(app != line for app, timestamp in result):
      result.append((line, timestamp))
      if len(result) == size:
        return tuple(result)
  return tuple(result)

build_absolute_url = lambda url='': os.path.join('https://tuxapp.org/', url)

build_actions = lambda *children: \
  join_elements(
    build_style('''
    @media (min-width: 30em) {
      .actions {
        float: right;
        margin: 0 0 0 0.5em;
      }
    }
    .actions > * {
      margin-right: 0.5em;
    }
    .actions > :last-child {
      margin-right: 0;
    }
    '''),
    build_tag('p.actions', None, *children),
  )

build_added_feed = lambda: build_feed(get_added_feed_url(), get_added_feed_name(), read_added_apps(1)[0][1], (build_app_feed_entry(app, timestamp) for app, timestamp in read_added_apps(25)))

build_app_card = lambda app, is_heading=False: build_card(query_data_uri(get_app_icon_path(app, tuxapp.query_appfile(app, 'icon-url')), 96 if is_heading else 64), tuxapp.query_appfile(app, 'name'), tuxapp.query_appfile(app, 'title'), get_app_url(app), utilities.query_data((app, 'version')), 'free license' if tuxapp.query_appfile(app, 'free-license') else '', is_heading)

build_app_feed_entry = \
  tuxapp.memoize(
    lambda app, timestamp: \
      build_tag('entry', None,
        build_tag('category', term=filter_category_name(tuxapp.query_appfile(app, 'category'))),
        build_tag('content', None,
          '<![CDATA[',
          get_app_icon_path(app, tuxapp.query_appfile(app, 'icon-url')) and build_tag('img', src=query_data_uri(get_app_icon_path(app, tuxapp.query_appfile(app, 'icon-url')), 96), style='float: right'),
          build_app_info(app),
          ']]>',
        type='html'),
        build_tag('id', build_absolute_url(get_app_url(app))),
        build_tag('link', href=get_app_url(app)),
        build_tag('title', ' - '.join((tuxapp.query_appfile(app, 'name'), tuxapp.query_appfile(app, 'title')))),
        build_tag('updated', build_atom_datetime(timestamp)),
      )
  )

build_app_gallery = lambda app: \
  join_elements(
    build_style('''
    .app-gallery {
      margin: 1em -0.125em;
    }
    .app-gallery .thumbnail {
      box-sizing: border-box;
      display: inline-block;
      padding: 0.125em;
      text-align: center;
      vertical-align: middle;
      width: 50%;
    }
    @media (min-width: 30em) {
      .app-gallery .thumbnail {
        width: 33.3%;
      }
    }
    @media (min-width: 40em) {
      .app-gallery .thumbnail {
        width: 25%;
      }
    }
    @media (min-width: 48em) {
      .app-gallery .thumbnail {
        width: 20%;
      }
    }
    .app-gallery .thumbnail img,
    .app-gallery .thumbnail video {
      display: block;
      max-height: 10em;
      max-width: 100%;
    }
    .app-gallery .thumbnail.is-video img,
    .app-gallery .thumbnail.is-video video {
      border-radius: 0.75em;
    }
    '''),
    build_tag('.app-gallery', None, *(
      tuple(build_thumbnail('Screenshot', get_app_url(app), get_app_screenshot_path(app, url)) for url in utilities.query_data((app, 'screenshot-urls')).split()) + \
      tuple(build_thumbnail('Video', get_app_url(app), get_app_video_thumbnail_pattern(app, video_url) if thumbnail_url == '-' else get_app_video_thumbnail_path(app, thumbnail_url), video_url) for video_url, thumbnail_url in zip(utilities.query_data((app, 'video-urls')).split(), utilities.query_data((app, 'video-thumbnail-urls')).split())))
    ),
  )

build_app_image = lambda app: \
  join_elements(
    build_style('''
    .app-image {
      margin: 1em 0;
    }
    @media (min-width: 40em) {
      .app-image {
        float: right;
        margin-left: 1em;
        margin-top: 0;
        max-width: 50%;
      }
    }
    .app-image .thumbnail,
    .app-image .thumbnail img {
      display: block;
    }
    .app-image .thumbnail img {
      max-height: 15em;
      max-width: 100%;
    }
    '''),
    utilities.query_data((app, 'image-url')) and build_tag('.app-image', None, build_thumbnail('Image', get_app_url(app), get_app_image_path(app, utilities.query_data((app, 'image-url'))))),
  )

build_app_info = lambda app: \
  join_elements(
    build_tag('dt', 'Category:'),
    build_tag('dd', None, build_tag('a', filter_category_name(tuxapp.query_appfile(app, 'category')), href=get_category_url(tuxapp.query_appfile(app, 'category')))),
    build_tag('dt', 'Group:'),
    build_tag('dd', None, build_tag('a', filter_group_name(tuxapp.query_appfile(app, 'group')), href=get_group_url(tuxapp.query_appfile(app, 'group')))),
    build_tag('dt', 'Free license:'),
    build_tag('dd', tuxapp.query_appfile(app, 'free-license')),
    build_tag('dt', 'Homepage:'),
    build_tag('dd', None, build_tag('a', tuxapp.query_appfile(app, 'homepage-url'), href=tuxapp.query_appfile(app, 'homepage-url'))),
    join_elements(
      build_tag('dt', 'GitHub repository:'),
      build_tag('dd', None, build_tag('a', utilities.query_data((app, 'github-repository')), href=utilities.build_github_url(utilities.query_data((app, 'github-repository'))))),
    ) \
      if utilities.query_data((app, 'github-repository')) else \
    '',
    build_tag('dt', 'Version:'),
    build_tag('dd', utilities.query_data((app, 'version')), utilities.query_data((app, 'changelog-url')) and ' ({})'.format(build_tag('a', 'changelog', href=utilities.query_data((app, 'changelog-url'))))),
    build_tag('dt', 'Downloads:'),
    build_tag('dd', None,
      build_tag('a', utilities.query_data((app, 'downloads-url')), href=utilities.query_data((app, 'downloads-url'))) \
        if utilities.query_data((app, 'downloads-url')) else \
      build_tag('a', tuxapp.query_appfile(app, 'homepage-url'), href=tuxapp.query_appfile(app, 'homepage-url')),
      escape_html(' ({})'.format(', '.join(re.findall(r'^download-(.+)-url=.', tuxapp.read_appfile(app), re.M)))),
    ),
    join_elements(
      build_tag('dt', 'Distribution formats:'),
      build_tag('dd', None,
        build_tag('span', '≈ ', title='Detected automatically, may be inaccurate'),
        escape_html(', '.join(get_format_name(format) for format in utilities.query_data((app, 'download-formats')).split())),
      ),
    ) \
      if utilities.query_data((app, 'download-formats')) else \
    '',
  )

build_app_instructions = lambda app: \
  join_elements(
    build_tag('h2', 'How to install'),
    build_tag('p', None, 'Run this command from the terminal to install {} using the {} script hosted on {}:'.format(build_tag('code', app), build_tag('code', tuxapp.get_name()), build_tag('a', 'GitHub', href=tuxapp.build_github_url('blob/master/tuxapp')))),
    build_tag('pre', None, build_command(r'python <(url={}; wget -O - $url || curl $url) {}'.format(tuxapp.build_github_raw_url(tuxapp.get_name()), app))),
    build_tag('p', None, 'Alternatively, you may also download the {} script and run it locally to install {}:'.format(build_tag('code', tuxapp.get_name()), build_tag('code', app))),
    build_tag('pre', None, '\n'.join(build_command(command) for command in (
      r'url={}; wget $url || curl -o {} $url'.format(tuxapp.build_github_raw_url(tuxapp.get_name()), tuxapp.get_name()),
      r'chmod +x ./{}'.format(tuxapp.get_name()),
      r'./{} {}'.format(tuxapp.get_name(), app),
    ))),
    build_tag('p', None, 'The app will run sandboxed (isolated from your system and sensitive files) if {} is installed. For example, use this command to install it on Debian/Ubuntu:'.format(build_tag('a', 'Firejail', href='https://firejail.wordpress.com/'))),
    build_tag('pre', None, build_command(r'sudo apt install firejail')),
  )

build_app_og_image_url = lambda app: \
  get_file_url(get_app_image_path(app, utilities.query_data((app, 'image-url')))) \
    if utilities.query_data((app, 'image-url')) else \
  get_file_url(get_app_icon_path(app, tuxapp.query_appfile(app, 'icon-url')))

build_app_page = lambda app: \
  join_elements(
    build_head(description=tuxapp.query_appfile(app, 'description') or tuxapp.query_appfile(app, 'title'), image=build_app_og_image_url(app), title='Install {} with {}'.format(tuxapp.query_appfile(app, 'name'), get_name()), url=get_app_url(app)),
    build_base(get_app_page_path(app)),
    build_title(tuxapp.query_appfile(app, 'name'), filter_category_name(tuxapp.query_appfile(app, 'category'))),
    build_header(),
    build_json_ld(get_app_json_ld(app)),
    build_actions(
      build_tag('a', 'Edit appfile', href=tuxapp.build_github_url('edit/master/apps/{}'.format(app))),
      build_tag('a', 'Report issue', href=tuxapp.build_github_url('issues/new?title={}'.format(app))),
    ),
    build_breadcrumbs(
      build_tag('a', filter_category_name(tuxapp.query_appfile(app, 'category')), href=get_category_url(tuxapp.query_appfile(app, 'category'))),
      build_tag('h1', tuxapp.query_appfile(app, 'name')),
    ),
    build_app_card(app, True),
    build_app_image(app),
    tuxapp.query_appfile(app, 'description') and build_tag('p', tuxapp.query_appfile(app, 'description')),
    tuxapp.query_appfile(app, 'note') and build_tag('p', tuxapp.query_appfile(app, 'note')),
    build_app_info(app),
    build_app_gallery(app),
    build_app_instructions(app),
    build_footer(),
  )

build_atom_datetime = lambda timestamp: '{}Z'.format(datetime.datetime.fromtimestamp(timestamp).isoformat())

build_base = lambda path: build_tag('base', href=os.path.relpath(get_build_path(), os.path.dirname(path)))

build_breadcrumbs = lambda *children: \
  join_elements(
    build_style('''
    .breadcrumbs {
      margin: 1em 0;
    }
    .breadcrumbs h1 {
      display: inline;
      font-size: inherit;
    }
    '''),
    build_tag('.breadcrumbs', None, escape_html(' > ').join((build_tag('a', 'Home', href=''),) + children)),
  )

build_card = lambda icon_url, name, title, url=None, name_tag='', title_tag='', is_heading=False, count=None: \
  join_elements(
    build_style('''
    .card {
      margin: 1em 0;
    }
    '''),
    build_flag(
      '.card{}{}'.format('.is-category' if url and url.startswith(get_category_url('')) else '', '.is-heading' if is_heading else ''),
      build_style('''
      .card-icon {
        height: 2em;
        min-width: 2em;
      }
      .card.is-category .card-icon,
      .card.is-heading .card-icon {
        height: 3em;
        min-width: 3em;
      }
      .card-icon img {
        margin: 0 auto;
        max-width: 100%;
      }
      '''),
      build_tag('.card-icon', None, build_tag('img', alt='Icon', src=icon_url)),
      build_tag('', None,
        build_style('''
        .card-name {
          font-size: larger;
          font-weight: bold;
        }
        .card.is-heading .card-name {
          font-size: x-large;
        }
        .card-name > :first-child {
          margin-right: 0.375em;
        }
        .card.is-heading .card-name .card-tag {
          font-size: medium;
        }
        '''),
        build_tag('.card-name', None,
          build_tag('span', name),
          name_tag and build_card_tag(name_tag),
          build_style('''
          .card-count {
            color: ''' + get_text_color() + ''';
            display: inline-block;
            font-weight: normal;
            margin-left: 0.25em;
          }
          '''),
          build_tag('span.card-count', '({})'.format(count)) if count else '',
        ),
        build_style('''
        .card-title {
          display: inline-block;
        }
        a .card-title {
          color: ''' + get_text_color() + ''';
        }
        .card.is-heading .card-title {
          font-weight: bold;
        }
        .card-title > :first-child {
          margin-right: 0.5em;
        }
        '''),
        build_tag('.card-title', None,
          build_tag('span', title),
          title_tag and build_card_tag(title_tag),
        ),
      ), href=not is_heading and url,
    ),
  )

build_card_tag = lambda text: \
  join_elements(
    build_style('''
    .card-tag {
      color: grey;
      display: inline-block;
      font-size: small;
      font-weight: normal;
    }
    '''),
    build_tag('span.card-tag', text),
  )

build_category_page = lambda category: \
  join_elements(
    build_head(description=' - '.join((filter_category_name(category), get_category_description(category), get_description()))),
    build_base(get_category_page_path(category)),
    build_title(filter_category_name(category)),
    build_header(),
    build_breadcrumbs(build_tag('h1', filter_category_name(category))),
    build_tag('p', get_category_description(category, True)),
    build_tag('p', 'Groups: ', ', '.join(build_tag('a', filter_group_name(group), href=get_group_url(group)) for group in sorted(set(tuxapp.query_appfile(app, 'group') for app in get_apps() if tuxapp.query_appfile(app, 'category') == category)))),
  )

build_columns = lambda *children: \
  join_elements(
    # https://stackoverflow.com/q/7785374
    build_style('''
    @media (min-width: 40em) {
      .columns {
        -moz-column-count: 2;
        -webkit-column-count: 2;
        column-count: 2;
      }
      .columns > * {
        -webkit-column-break-inside: avoid;
        break-inside: avoid;
        page-break-inside: avoid;
      }
      .columns > :first-child {
        margin-top: 0;
      }
      .columns > :last-child {
        margin-bottom: 0;
      }
    }
    @media (min-width: 60em) {
      .columns {
        -moz-column-count: 3;
        -webkit-column-count: 3;
        column-count: 3;
      }
    }
    '''),
    build_tag('.columns', None, *children),
  )

build_combined_styles = lambda: build_tag('combined-styles')

build_command = lambda command: \
  join_elements(
    build_style('''
    .command {
      user-select: all;
      white-space: pre-wrap;
    }
    '''),
    build_tag('code.command', command),
  )

build_data_uri_key = lambda path, width=None: ('data-uri', tuxapp.hash_md5(os.path.basename(path)), str(width))

build_feed = lambda url, name, timestamp, entries: \
  join_elements(
    '<?xml version="1.0" encoding="utf-8"?>',
    build_tag('feed', None,
      build_tag('icon', build_logo_url()),
      build_tag('id', build_absolute_url(url)),
      build_tag('link', href=''),
      build_tag('link', href=url, rel='self'),
      build_tag('logo', build_logo_url()),
      build_tag('rights', get_copyright()),
      build_tag('subtitle', get_description()),
      build_title(name),
      build_tag('updated', build_atom_datetime(timestamp)),
      *entries, xmlns='http://www.w3.org/2005/Atom', **{'xml:base': build_absolute_url()}
    ),
  )

build_feed_link = lambda url: \
  join_elements(
    build_style('''
    .feed-link {
      font-size: small;
      margin-left: 0.5em;
      vertical-align: super;
    }
    '''),
    build_tag('a.feed-link', 'Feed', href=url),
  )

build_flag = lambda selector, *children, **attributes: \
  join_elements(
    build_style('''
    .flag {
      display: block;
      width: 100%;
    }
    .flag > * {
      display: table-cell;
      vertical-align: middle;
    }
    .flag > :first-child {
      padding-right: 0.5em;
    }
    .flag > :first-child img {
      display: block;
    }
    .flag > :last-child {
      width: 100%;
    }
    '''),
    build_tag('{}.flag{}'.format('a' if attributes.get('href') else '', selector), None, *children, **attributes),
  )

build_footer = \
  tuxapp.memoize(
    lambda: \
      join_elements(
        build_separator(),
        build_actions(
          build_tag('a', 'Source code', href=tuxapp.build_github_url()),
          build_tag('a', 'Issues', href=tuxapp.build_github_url('issues')),
        ),
        build_style('''
        .footer-copyright {
          color: grey;
          font-size: smaller;
        }
        '''),
        build_tag('.footer-copyright', None,
          build_tag('p', get_copyright()),
          build_tag('p', 'Linux® is the registered trademark of Linus Torvalds in the U.S. and other countries.'),
          build_tag('p', None, 'Hosting is sponsored by {}.'.format(build_tag('a', 'DigitalOcean', href='https://www.digitalocean.com/'))),
        ),
        build_script(r'''
        if (location.protocol == 'file:') {
          Array.prototype.forEach.call(document.querySelectorAll('a'), function(element) {
            if (~element.href.indexOf('file:///') && element.pathname.slice(-1) == '/') element.pathname += 'index.html';
          });
          Array.prototype.forEach.call(document.querySelectorAll('form'), function(element) {
            if (~element.action.indexOf('file:///') && element.action.slice(-1) == '/') element.action += 'index.html';
          });
        }
        '''),
      )
  )

build_group_page = lambda group: \
  join_elements(
    build_head(description=' - '.join((filter_group_name(group), get_description()))),
    build_base(get_group_page_path(group)),
    build_title(filter_group_name(group)),
    build_header(),
    build_breadcrumbs(build_tag('h1', filter_group_name(group))),
    build_tag('p', 'Categories: ', ', '.join(build_tag('a', filter_category_name(category), href=get_category_url(category)) for category in sorted(set(tuxapp.query_appfile(app, 'category') for app in get_apps() if tuxapp.query_appfile(app, 'group') == group)))),
  )

build_head = \
  tuxapp.memoize(
    lambda **overrides: \
      join_elements(
        '<!DOCTYPE html>',
        '<html lang="en">',
        build_tag('meta', charset='utf-8'),
        build_tag('meta', content=get_name(), name='application-name'),
        build_tag('meta', content=overrides.get('description', get_description()), name='description'),
        build_tag('meta', content='width=device-width, initial-scale=1', name='viewport'),
        build_tag('meta', content=overrides.get('description', get_description()), property='og:description'),
        build_tag('meta', content=build_absolute_url(overrides.get('image', build_logo_url())), property='og:image'),
        build_tag('meta', content=get_name(), property='og:site_name'),
        build_tag('meta', content=overrides.get('title', get_name()), property='og:title'),
        build_tag('meta', content='website', property='og:type'),
        build_tag('meta', content=build_absolute_url(overrides.get('url', '')), property='og:url'),
        build_tag('link', href=get_added_feed_url(), rel='alternate', title=get_added_feed_name(), type='application/atom+xml'),
        build_tag('link', href=get_updated_feed_url(), rel='alternate', title=get_updated_feed_name(), type='application/atom+xml'),
        build_tag('link', href=query_data_uri(get_logo_path()), rel='icon'),
        build_json_ld(get_json_ld()),
        build_combined_styles(),
        build_style('''
        :link {
          color: mediumblue;
        }
        :visited {
          color: navy;
        }
        :link:active,
        :visited:active {
          color: red;
        }
        a {
          transition: opacity 0.2s;
        }
        a:hover {
          opacity: 0.75;
        }
        body {
          color: ''' + get_text_color() + ''';
          font-family: sans-serif;
          margin: 1em auto;
          max-width: 60em;
          padding: 0 1em;
          word-wrap: break-word;
        }
        '''),
      )
  )

build_header = \
  tuxapp.memoize(
    lambda: \
      join_elements(
        build_flag('',
          build_style('''
          .header-logo {
            height: 3.5em;
            min-width: 3.5em;
          }
          .header-logo img {
            max-width: 100%;
          }
          '''),
          build_tag('a.header-logo', None, build_tag('img', alt='Logo', src=query_data_uri(get_logo_path(), 112)), href='', title='Home'),
          build_tag('', None,
            build_style('''
            .header-top > :last-child {
              display: block;
            }
            @media (min-width: 30em) {
              .header-top > :last-child {
                display: table-cell;
                text-align: right;
              }
            }
            '''),
            build_flag('.header-top',
              build_style('''
              .header-name {
                color: inherit;
                font-family: serif;
                font-size: xx-large;
                text-decoration: none;
                white-space: nowrap;
              }
              '''),
              build_tag('a.header-name', get_name(), href='', title='Home'),
              build_tag('form.header-search', None,
                build_tag('input', name='query', placeholder='Search', type='search'),
                build_script(r'document.querySelector(".header-search").query.value = decodeURIComponent((location.search.match(/\bquery=([^&]+)/) || [undefined, ""])[1].replace(/\+/g, " "));'),
              action=get_search_url()),
            ),
            build_style('''
            .header-description {
              color: grey;
              font-style: italic;
            }
            '''),
            build_tag('.header-description', get_description()),
          ),
        ),
        build_separator(),
      )
  )

build_json_ld = lambda schema: build_script(build_json(schema), 'application/ld+json')

build_lightbox_script = lambda: \
  build_script(r'''
  var scrollTop = 0;

  function getElement(selector, url) {
    var element = document.getElementById((url || location.href).split('#', 2)[1]);
    if (element) return element.querySelector(selector);
  }

  function main() {
    addEventListener('hashchange', function(event) {
      onURL(event.newURL, event.oldURL);
    });
    addEventListener('keydown', function(event) {
      if (onKeyCode(event.keyCode)) event.preventDefault();
    });
    addEventListener('scroll', updateScrollTop);
  }

  function onKeyCode(keyCode) {
    if (getElement('.lightbox-action')) {
      if (keyCode == 27) location = getElement('.lightbox-action.is-close').href;
      else if (keyCode == 37 && getElement('.lightbox-action.is-previous').hash) location = getElement('.lightbox-action.is-previous').href;
      else if (keyCode == 39 && getElement('.lightbox-action.is-next').hash) location = getElement('.lightbox-action.is-next').href;
      else return true;
    }
  }

  function onURL(url, previousURL) {
    scrollTo(0, scrollTop);
    if (/#$/.test(url)) history.replaceState({}, '', location.href.slice(0, -1));
    if (getElement('video', previousURL)) getElement('video', previousURL).pause();
    else if (getElement('iframe', previousURL)) getElement('iframe', previousURL).contentWindow.postMessage('{ "event": "command", "func": "pauseVideo", "args": "" }', '*');
  }

  function updateScrollTop() {
    scrollTop = document.documentElement.scrollTop || document.body.scrollTop;
  }

  main();
  ''')

build_logo_url = lambda: get_file_url(copy_updated_file(get_logo_path(), os.path.join(get_build_path(), os.path.basename(get_logo_path()))))

build_main_page = lambda: \
  join_elements(
    build_head(),
    build_base(get_main_page_path()),
    build_title(),
    build_header(),
    build_tag('h2', 'Categories'),
    build_columns(*(build_card(query_data_uri(get_category_icon_path(category)), filter_category_name(category), get_category_description(category), get_category_url(category), '', '', False, count) for category, count in get_categories())),
    build_tag('h2', 'Groups'),
    build_columns(*(build_tag('', None,
      build_tag('a', filter_group_name(group), href=get_group_url(group)),
      build_tag('span', ' ({})'.format(count)),
    ) for group, count in get_groups())),
    build_tag('h2', get_updated_feed_name(), build_feed_link(get_updated_feed_url())),
    build_columns(*(build_app_card(app) for app, timestamp in query_updated_apps(15))),
    build_tag('h2', get_added_feed_name(), build_feed_link(get_added_feed_url())),
    build_columns(*(build_app_card(app) for app, timestamp in read_added_apps(15))),
    build_footer(),
  )

build_script = lambda script, type=None: \
  build_tag('script', None,
    ('' if type else '(function(){') + \
    remove_whitespace(script) + \
    ('' if type else '})();'),
  type=type)

build_search_page = lambda: \
  join_elements(
    build_head(),
    build_base(get_search_page_path()),
    build_title('Search results'),
    build_header(),
    build_breadcrumbs(build_tag('h1', 'Search results')),
    build_tag('p.search-stats', None, build_tag('noscript', 'Search requires JavaScript to be enabled in your browser.')),
    build_tag('.search-results'),
    build_style('''
    .search-highlight,
    .search-link {
      font-weight: bold;
    }
    '''),
    build_script(r'''
    function buildResults(items) {
      return items.reduce(function(result, item) {
        return result +
          '<p>' +
          '<a class="search-link" href="''' + get_app_url('\' + encodeURIComponent(item.name) + \'') + r'''">' + escapeHTML(getAppName(item.name)) + '</a>' +
          '<br>' +
          escapeHTML(buildSnippet(item.text_matches) && buildSnippet(item.text_matches) + '...').replace(/\[MATCH\]/g, '<span class="search-highlight">').replace(/\[\/MATCH\]/g, '</span>') +
          '</p>';
      }, '');
    }

    function buildSnippet(matches) {
      return matches.map(function(match) {
        return filterSnippetFragment(match.fragment, match.matches).split('\n').map(function(line) {
          return line.replace(/[''' + ''.join(validation.get_punctuation()) + r''']+$/, '');
        }).map(function(line) {
          if (~getSnippetFields().concat('').indexOf(line.split('=', 1)[0])) return line.replace(/^.*?=/, '');
        }).filter(Boolean).join('... ');
      }).filter(Boolean).join('... ');
    }

    function buildStats(count) {
      return (count || 'No') + ' ' + (count == 1 ? 'result' : 'results') + ' for \'' + document.querySelector('.header-search').query.value + '\'.';
    }

    function escapeHTML(string) {
      return new Option(string).innerHTML;
    }

    function filterSnippetFragment(fragment, matches) {
      return matches.reduce(function(result, match, index) {
        return result + fragment.slice((matches[index - 1] || { indices: [undefined, 0] }).indices[1], match.indices[0]) + '[MATCH]' + fragment.slice(match.indices[0], match.indices[1]) + '[/MATCH]';
      }, '') + fragment.slice((matches[matches.length - 1] || { indices: [undefined, 0] }).indices[1]);
    }

    function getAppName(app) {
      return ''' + build_json(dict((app, tuxapp.query_appfile(app, 'name')) for app in get_apps())) + r'''[app] || app;
    }

    function getSnippetFields() {
      return [
        'description',
        'name',
        'title',
      ];
    }

    function main() {
      if (document.querySelector('.header-search').query.value) {
        render('Searching...');
        request(renderResponse);
      }
      else render('', 'No search query.');
    }

    function render(stats, results) {
      document.querySelector('.search-stats').textContent = stats;
      document.querySelector('.search-results').innerHTML = results || '';
    }

    function renderResponse(response) {
      render(buildStats(response.total_count), buildResults(response.items));
    }

    function request(onResponse) {
      var xhr = new XMLHttpRequest();
      xhr.addEventListener('load', function(event) {
        onResponse(JSON.parse(event.target.responseText));
      });
      xhr.open('GET', 'https://api.github.com/search/code?q=repo:' + encodeURIComponent("''' + tuxapp.get_github_repository() + r'''") + '+path:apps+' + encodeURIComponent(document.querySelector('.header-search').query.value));
      xhr.setRequestHeader('Accept', 'application/vnd.github.v3.text-match+json');
      xhr.send();
    }

    main();
    '''),
    build_footer(),
  )

build_separator = lambda: \
  join_elements(
    build_style('''
    .separator {
      background: lightgrey;
      border: none;
      clear: both;
      height: 1px;
      margin: 1em 0;
    }
    '''),
    build_tag('hr.separator'),
  )

build_style = lambda style: get_style_prefix() + remove_whitespace(style) + get_style_suffix()

build_tag = lambda selector, text=None, *children, **attributes: \
  '<{}{}{}>{}{}{}'.format(
    extract_tag_name(selector),
    build_tag_attributes(selector, attributes) if attributes or '#' in selector or '.' in selector else '',
    '' if children or extract_tag_name(selector) not in get_void_elements() else '/',
    escape_html(text) if text else '',
    ''.join(children),
    '</{}>'.format(extract_tag_name(selector)) if children or extract_tag_name(selector) not in get_void_elements() else '',
  )

build_tag_attributes = lambda selector, attributes={}: \
  ''.join(' {}{}'.format(name, '' if value is True else '="{}"'.format(escape_html(str(value) if isinstance(value, int) else value))) for name, value in sorted(dict(attributes, **{
    'class': ' '.join(re.findall(r'(?<=\.)[^#.]+', selector)) or None,
    'id': ' '.join(re.findall(r'(?<=#)[^#.]+', selector)) or None,
  }).items()) if value or value is '')

build_thumbnail = lambda text, url, path, video_url=None: \
  join_elements(
    build_tag('a.thumbnail.{}'.format('is-video' if video_url else 'is-screenshot'), None,
      build_tag('video', preload='metadata', src=video_url) \
        if video_url and not os.path.isfile(path) else \
      build_tag('img', alt=text, src=get_file_url(path)),
    href='{}#{}'.format(url, os.path.splitext(os.path.basename(path))[0])),
    build_style('''
    .lightbox {
      background: rgba(0, 0, 0, 0.75);
      bottom: 0;
      display: none;
      left: 0;
      position: fixed;
      right: 0;
      top: 0;
    }
    .lightbox:target {
      display: block;
    }
    .lightbox iframe,
    .lightbox img,
    .lightbox video {
      -webkit-transform: translate(-50%, -50%);
      left: 50%;
      max-height: 90vh;
      max-width: 90vw;
      position: absolute;
      top: 50%;
      transform: translate(-50%, -50%);
    }
    .lightbox iframe {
      border: none;
    }
    '''),
    build_tag('#{}.lightbox'.format(os.path.splitext(os.path.basename(path))[0]), None,
      build_tag('iframe', allowfullscreen=True, height=480, src='https://www.youtube.com/embed/{}?enablejsapi=1'.format(tuxapp.search(r'(?<=^https://www\.youtube\.com/watch\?v=)[^&]+', video_url)), width=853) \
        if video_url and tuxapp.parse_url(video_url).netloc == 'www.youtube.com' else \
      build_tag('video', controls=True, preload='metadata', src=video_url) \
        if video_url else \
      build_tag('img', alt=text, src=get_file_url(path)),
      build_style('''
      .lightbox-action {
        color: white;
        font-size: 2.5em;
        position: absolute;
        text-align: center;
        text-decoration: none;
        width: 1.2em;
      }
      .lightbox-action.is-close {
        right: 0;
        top: 0;
      }
      .lightbox-action.is-next,
      .lightbox-action.is-previous {
        margin-top: -0.6em;
        top: 50%;
      }
      .lightbox-action.is-next[href$="#"],
      .lightbox-action.is-previous[href$="#"] {
        visibility: hidden;
      }
      .lightbox-action.is-next {
        right: 0;
      }
      .lightbox-action.is-previous {
        left: 0;
      }
      '''),
      build_tag('a.lightbox-action.is-close', '×', href='{}#'.format(url), title='Close'),
      build_tag('a.lightbox-action.is-next', '▸', href='{}#'.format(url), title='Next'),
      build_tag('a.lightbox-action.is-previous', '◂', href='{}#'.format(url), title='Previous'),
    ),
  )

build_title = lambda *components: build_tag('title', ' - '.join(components + (get_name(),)))

build_updated_feed = lambda: build_feed(get_updated_feed_url(), get_updated_feed_name(), query_updated_apps(1)[0][1], (build_app_feed_entry(app, timestamp) for app, timestamp in query_updated_apps(25)))

copy_updated_file = lambda path, destination_path: \
  destination_path \
    if tuxapp.is_file_newer(path, destination_path) else \
  tuxapp.copy_file(path, destination_path)

extract_tag_name = lambda selector: selector.split('#', 1)[0].split('.', 1)[0] or 'div'

filter_category_name = lambda category: category.title()

filter_group_name = lambda group: group.replace('-', ' ').title()

generate_added_feed = lambda: tuxapp.write_file(get_added_feed_path(), build_added_feed())

generate_app_list_pages = lambda key, base_path, get_path, build: \
  tuxapp.remove_directory(base_path) and \
  all(os.path.isfile(get_path(tuxapp.query_appfile(app, key))) or tuxapp.write_file(get_path(tuxapp.query_appfile(app, key)), build(tuxapp.query_appfile(app, key))) for app in get_apps()) and \
  all(tuxapp.append_file(get_path(tuxapp.query_appfile(app, key)), build_app_card(app)) for app in sorted(get_apps())) and \
  all(tuxapp.write_file(path, process_styles(tuxapp.read_file(path) + build_footer())) for path in glob.iglob(get_path('*')))

generate_app_page = lambda app: tuxapp.write_file(get_app_page_path(app), process_lightbox(process_styles(build_app_page(app))))

generate_app_pages = lambda apps: utilities.call_parallel(generate_app_page_worker, apps)

generate_category_pages = lambda: generate_app_list_pages('category', get_categories_path(), get_category_page_path, build_category_page)

generate_group_pages = lambda: generate_app_list_pages('group', get_groups_path(), get_group_page_path, build_group_page)

generate_main_page = lambda: tuxapp.write_file(get_main_page_path(), process_styles(build_main_page()))

generate_pages = lambda: \
  all(tuxapp.remove_directory(get_app_path(app)) for app in get_apps() if not os.path.isfile(tuxapp.get_appfile_path(app))) and \
  generate_added_feed() and \
  generate_category_pages() and \
  generate_group_pages() and \
  generate_main_page() and \
  generate_search_page() and \
  generate_updated_feed() and \
  True

generate_search_page = lambda: tuxapp.write_file(get_search_page_path(), process_styles(build_search_page()))

generate_updated_feed = lambda: tuxapp.write_file(get_updated_feed_path(), build_updated_feed())

get_added_feed_name = lambda: 'New Apps'

get_added_feed_path = lambda: os.path.join(get_feeds_path(), 'added.xml')

get_added_feed_url = lambda: get_file_url(get_added_feed_path())

get_app_icon_path = \
  tuxapp.check('No icon for {}')(
    lambda app, url: next(glob.iglob(get_app_icon_pattern(app, url)), None)
  )

get_app_icon_pattern = lambda app, url=None: os.path.join(get_app_path(app), 'icon-{}.*'.format(tuxapp.hash_md5(url) if url else '*'))

get_app_image_path = \
  tuxapp.check('No image for {}')(
    lambda app, url: next(glob.iglob(get_app_image_pattern(app, url)), None)
  )

get_app_image_pattern = lambda app, url=None: os.path.join(get_app_path(app), 'image-{}.*'.format(tuxapp.hash_md5(url) if url else '*'))

get_app_json_ld = lambda app: \
  dict((key, value) for key, value in (
    ('@context', 'http://schema.org'),
    ('@type', 'SoftwareApplication'),
    ('applicationCategory', filter_category_name(tuxapp.query_appfile(app, 'category'))),
    ('description', tuxapp.query_appfile(app, 'description') or tuxapp.query_appfile(app, 'title')),
    ('image', build_absolute_url(build_app_og_image_url(app))),
    ('installUrl', build_absolute_url(get_app_url(app))),
    ('name', '{} on {}'.format(tuxapp.query_appfile(app, 'name'), get_name())),
    ('operatingSystem', 'Linux'),
    ('releaseNotes', utilities.query_data((app, 'changelog-url'))),
    ('screenshot', utilities.query_data((app, 'screenshot-urls')) and build_absolute_url(get_app_screenshot_path(app, utilities.query_data((app, 'screenshot-urls')).split()[0]))),
    ('softwareVersion', utilities.query_data((app, 'version'))),
    ('url', tuxapp.query_appfile(app, 'homepage-url')),
  ) if value)

get_app_page_path = lambda app: os.path.join(get_app_path(app), 'index.html')

get_app_path = lambda app: os.path.join(get_build_path(), 'apps/{}'.format(app))

get_app_screenshot_path = \
  tuxapp.check('No screenshot for {}')(
    lambda app, url: next(glob.iglob(get_app_screenshot_pattern(app, url)), None)
  )

get_app_screenshot_pattern = lambda app, url=None: os.path.join(get_app_path(app), 'screenshot-{}.*'.format(tuxapp.hash_md5(url) if url else '*'))

get_app_url = lambda app: get_file_url(get_app_page_path(app))

get_app_video_thumbnail_path = \
  tuxapp.check('No video thumbnail for {}')(
    lambda app, url: next(glob.iglob(get_app_video_thumbnail_pattern(app, url)), None)
  )

get_app_video_thumbnail_pattern = lambda app, url=None: os.path.join(get_app_path(app), 'video-{}.*'.format(tuxapp.hash_md5(url) if url else '*'))

get_apps = lambda: (tuxapp.extract_app(path) for path in glob.iglob(get_app_path('*')))

get_assets_path = lambda: os.path.join(tuxapp.get_project_path(), 'assets')

get_build_path = lambda: os.path.join(tuxapp.get_project_path(), 'build')

get_categories = lambda: tuple(sorted(collections.Counter(tuxapp.query_appfile(app, 'category') for app in get_apps()).items()))

get_categories_path = lambda: os.path.join(get_build_path(), 'categories')

get_category_description = lambda category, is_sentence=False: \
  {
    'audio': 'Applications for presenting, creating, or processing audio',
    'development': 'Applications for development',
    'education': 'Educational software',
    'game': 'Video games',
    'graphics': 'Applications for viewing, creating, or processing graphics',
    'network': 'Network applications',
    'office': 'Office type applications',
    'science': 'Scientific software',
    'settings': 'Settings applications',
    'system': 'System applications',
    'utility': 'Small utility applications',
    'video': 'Applications for presenting, creating, or processing video',
  }[category] + ('.' if is_sentence else '')

get_category_icon_path = lambda category: os.path.join(get_assets_path(), 'categories/{}.png'.format(category))

get_category_page_path = lambda category: os.path.join(get_categories_path(), '{}/index.html'.format(category))

get_category_url = lambda category: get_file_url(get_category_page_path(category))

get_copyright = lambda: '© {} {}'.format(tuxapp.get_copyright_range(), get_name())

get_description = lambda: 'An open catalog of easily installable and up-to-date Linux® applications'

get_feeds_path = lambda: os.path.join(get_build_path(), 'feeds')

get_file_url = lambda path: re.sub(r'/index\.html$', '/', os.path.relpath(path, get_build_path()))

get_format_name = lambda format: \
  {
    'appimage': 'AppImage',
    'deb': 'deb',
    'flatpak': 'Flatpak',
    'rpm': 'rpm',
    'snap': 'snap',
    'tar': 'tarball',
  }.get(format, format.title())

get_group_page_path = lambda group: os.path.join(get_groups_path(), '{}/index.html'.format(group))

get_group_url = lambda group: get_file_url(get_group_page_path(group))

get_groups = lambda: tuple(sorted(collections.Counter(tuxapp.query_appfile(app, 'group') for app in get_apps()).items()))

get_groups_path = lambda: os.path.join(get_build_path(), 'groups')

get_json_ld = lambda: \
  (
    {
      '@context': 'http://schema.org',
      '@type': 'WebSite',
      'description': get_description(),
      'image': build_absolute_url(build_logo_url()),
      'name': get_name(),
      'url': build_absolute_url(),
    },
    {
      '@context': 'http://schema.org',
      '@type': 'SoftwareApplication',
      'description': tuxapp.get_description(),
      'image': build_absolute_url(build_logo_url()),
      'name': tuxapp.get_name(),
      'operatingSystem': 'Linux',
      'softwareVersion': tuxapp.get_version(),
      'url': build_absolute_url(),
    },
  )

get_logo_path = lambda: os.path.join(get_assets_path(), 'logo.png')

get_main_page_path = lambda: os.path.join(get_build_path(), 'index.html')

get_name = lambda: 'TuxApp'

get_search_page_path = lambda: os.path.join(get_build_path(), 'search/index.html')

get_search_url = lambda: get_file_url(get_search_page_path())

get_style_prefix = lambda: '<!-- <style>'

get_style_regex = lambda: re.compile(r'{}(.*?){}'.format(re.escape(get_style_prefix()), re.escape(get_style_suffix())), re.S)

get_style_suffix = lambda: '</style> -->'

get_text_color = lambda: '#222'

get_updated_feed_name = lambda: 'Updated Apps'

get_updated_feed_path = lambda: os.path.join(get_feeds_path(), 'updated.xml')

get_updated_feed_url = lambda: get_file_url(get_updated_feed_path())

get_void_elements = lambda: \
  (
    'area',
    'base',
    'br',
    'col',
    'embed',
    'hr',
    'img',
    'input',
    'keygen',
    'link',
    'meta',
    'param',
    'source',
    'track',
    'wbr',
  )

join_elements = lambda *elements: ''.join(elements)

process_lightbox = lambda html: process_lightbox_previous(process_lightbox_next(html)) + build_lightbox_script()

process_lightbox_next = lambda html: re.sub(r' class="lightbox-action is-next" href=".*?#(?=")', lambda match: match.group() + (re.compile(r'(?<= class="lightbox" id=")[^"]+').findall(html, match.start()) + [''])[0], html) # pylint: disable=undefined-variable

process_lightbox_previous = lambda html: re.sub(r' class="lightbox-action is-previous" href=".*?#(?=")', lambda match: match.group() + ([''] + re.compile(r'(?<= class="lightbox" id=")[^"]+').findall(html, 0, match.start()))[-2], html) # pylint: disable=undefined-variable

process_styles = lambda html: get_style_regex().sub('', html).replace(build_combined_styles(), build_tag('style', None, *functools.reduce(lambda styles, style: styles if style in styles else styles + (style,), get_style_regex().findall(html), ())))

query_data_uri = lambda path, width=None: \
  utilities.query_data(build_data_uri_key(path, width)) or \
  utilities.update_data(build_data_uri_key(path, width), build_data_uri(path, width)) and \
  utilities.query_data(build_data_uri_key(path, width))

query_updated_apps = lambda size: tuple((row[0].split(':', 1)[0], int(row[1])) for rows in iter(utilities.connect_data().execute('SELECT key, value FROM items WHERE key LIKE "%:timestamp" ORDER BY value DESC LIMIT ?', (size,)).fetchmany, []) for row in rows)

remove_whitespace = lambda string: re.sub(r'^\s+', '', string, 0, re.M).replace('\n', '')

resize_image = lambda path, width: \
  utilities.install_missing_package('imagemagick', 'convert') and \
  tuxapp.read_process_binary(('convert', '-resize', '{}>'.format(width), '{}:{}'.format(utilities.detect_image_extension(path), path), '-'))
