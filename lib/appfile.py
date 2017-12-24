# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

get_categories = lambda: \
  (
    'audio',
    'development',
    'education',
    'game',
    'graphics',
    'network',
    'office',
    'science',
    'settings',
    'system',
    'utility',
    'video',
  )

get_default_package_repository = lambda: 'stretch'

get_groups = lambda: \
  (
    'audio-streaming',
    'cloud-storage',
    'code-editors',
    'content-management',
    'cryptocurrency-wallets',
    'database-management',
    'ebook-utilities',
    'email-clients',
    'file-managers',
    'game-stores',
    'image-editors',
    'instant-messengers',
    'integrated-development-environments',
    'markup-editors',
    'monitoring-applications',
    'note-taking',
    'office-suits',
    'productivity-tools',
    'racing-games',
    'role-playing',
    'screen-capture',
    'sports-utilities',
    'version-control',
    'video-editing',
    'video-streaming',
    'web-browsers',
    'web-development',
  )

get_keys = lambda: \
  (
    'category',
    'description',
    'desktop-entry',
    'download-x86-64-url',
    'download-x86-url',
    'executable',
    'firejail',
    'free-license',
    'group',
    'homepage-url',
    'icon-url',
    'ignored-libraries',
    'name',
    'note',
    'package-repository',
    'packages',
    'title',
    'version-regex',
    'version-url',
  )

get_package_repositories = lambda: \
  (
    'stretch',
    'xenial',
  )
