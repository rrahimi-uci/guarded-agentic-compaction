---
dataset_info:
  features:
  - name: url
    dtype: string
  - name: repository_url
    dtype: string
  - name: labels_url
    dtype: string
  - name: comments_url
    dtype: string
  - name: events_url
    dtype: string
  - name: html_url
    dtype: string
  - name: id
    dtype: int64
  - name: node_id
    dtype: string
  - name: number
    dtype: int64
  - name: title
    dtype: string
  - name: user
    struct:
    - name: avatar_url
      dtype: string
    - name: events_url
      dtype: string
    - name: followers_url
      dtype: string
    - name: following_url
      dtype: string
    - name: gists_url
      dtype: string
    - name: gravatar_id
      dtype: string
    - name: html_url
      dtype: string
    - name: id
      dtype: int64
    - name: login
      dtype: string
    - name: node_id
      dtype: string
    - name: organizations_url
      dtype: string
    - name: received_events_url
      dtype: string
    - name: repos_url
      dtype: string
    - name: site_admin
      dtype: bool
    - name: starred_url
      dtype: string
    - name: subscriptions_url
      dtype: string
    - name: type
      dtype: string
    - name: url
      dtype: string
    - name: user_view_type
      dtype: string
  - name: labels
    list:
    - name: color
      dtype: string
    - name: default
      dtype: bool
    - name: description
      dtype: string
    - name: id
      dtype: int64
    - name: name
      dtype: string
    - name: node_id
      dtype: string
    - name: url
      dtype: string
  - name: state
    dtype: string
  - name: locked
    dtype: bool
  - name: assignee
    struct:
    - name: avatar_url
      dtype: string
    - name: events_url
      dtype: string
    - name: followers_url
      dtype: string
    - name: following_url
      dtype: string
    - name: gists_url
      dtype: string
    - name: gravatar_id
      dtype: string
    - name: html_url
      dtype: string
    - name: id
      dtype: int64
    - name: login
      dtype: string
    - name: node_id
      dtype: string
    - name: organizations_url
      dtype: string
    - name: received_events_url
      dtype: string
    - name: repos_url
      dtype: string
    - name: site_admin
      dtype: bool
    - name: starred_url
      dtype: string
    - name: subscriptions_url
      dtype: string
    - name: type
      dtype: string
    - name: url
      dtype: string
    - name: user_view_type
      dtype: string
  - name: assignees
    list:
    - name: avatar_url
      dtype: string
    - name: events_url
      dtype: string
    - name: followers_url
      dtype: string
    - name: following_url
      dtype: string
    - name: gists_url
      dtype: string
    - name: gravatar_id
      dtype: string
    - name: html_url
      dtype: string
    - name: id
      dtype: int64
    - name: login
      dtype: string
    - name: node_id
      dtype: string
    - name: organizations_url
      dtype: string
    - name: received_events_url
      dtype: string
    - name: repos_url
      dtype: string
    - name: site_admin
      dtype: bool
    - name: starred_url
      dtype: string
    - name: subscriptions_url
      dtype: string
    - name: type
      dtype: string
    - name: url
      dtype: string
    - name: user_view_type
      dtype: string
  - name: milestone
    struct:
    - name: closed_at
      dtype: string
    - name: closed_issues
      dtype: int64
    - name: created_at
      dtype: string
    - name: creator
      struct:
      - name: avatar_url
        dtype: string
      - name: events_url
        dtype: string
      - name: followers_url
        dtype: string
      - name: following_url
        dtype: string
      - name: gists_url
        dtype: string
      - name: gravatar_id
        dtype: string
      - name: html_url
        dtype: string
      - name: id
        dtype: int64
      - name: login
        dtype: string
      - name: node_id
        dtype: string
      - name: organizations_url
        dtype: string
      - name: received_events_url
        dtype: string
      - name: repos_url
        dtype: string
      - name: site_admin
        dtype: bool
      - name: starred_url
        dtype: string
      - name: subscriptions_url
        dtype: string
      - name: type
        dtype: string
      - name: url
        dtype: string
      - name: user_view_type
        dtype: string
    - name: description
      dtype: string
    - name: due_on
      dtype: string
    - name: html_url
      dtype: string
    - name: id
      dtype: int64
    - name: labels_url
      dtype: string
    - name: node_id
      dtype: string
    - name: number
      dtype: int64
    - name: open_issues
      dtype: int64
    - name: state
      dtype: string
    - name: title
      dtype: string
    - name: updated_at
      dtype: string
    - name: url
      dtype: string
  - name: comments
    dtype: int64
  - name: created_at
    dtype: string
  - name: updated_at
    dtype: string
  - name: closed_at
    dtype: string
  - name: author_association
    dtype: string
  - name: active_lock_reason
    dtype: string
  - name: body
    dtype: string
  - name: closed_by
    struct:
    - name: avatar_url
      dtype: string
    - name: events_url
      dtype: string
    - name: followers_url
      dtype: string
    - name: following_url
      dtype: string
    - name: gists_url
      dtype: string
    - name: gravatar_id
      dtype: string
    - name: html_url
      dtype: string
    - name: id
      dtype: int64
    - name: login
      dtype: string
    - name: node_id
      dtype: string
    - name: organizations_url
      dtype: string
    - name: received_events_url
      dtype: string
    - name: repos_url
      dtype: string
    - name: site_admin
      dtype: bool
    - name: starred_url
      dtype: string
    - name: subscriptions_url
      dtype: string
    - name: type
      dtype: string
    - name: url
      dtype: string
    - name: user_view_type
      dtype: string
  - name: reactions
    struct:
    - name: '+1'
      dtype: int64
    - name: '-1'
      dtype: int64
    - name: confused
      dtype: int64
    - name: eyes
      dtype: int64
    - name: heart
      dtype: int64
    - name: hooray
      dtype: int64
    - name: laugh
      dtype: int64
    - name: rocket
      dtype: int64
    - name: total_count
      dtype: int64
    - name: url
      dtype: string
  - name: timeline_url
    dtype: string
  - name: performed_via_github_app
    dtype: 'null'
  - name: state_reason
    dtype: string
  - name: draft
    dtype: bool
  - name: pull_request
    struct:
    - name: diff_url
      dtype: string
    - name: html_url
      dtype: string
    - name: merged_at
      dtype: string
    - name: patch_url
      dtype: string
    - name: url
      dtype: string
  - name: is_pull_request
    dtype: bool
  - name: issue_comments
    sequence: string
  splits:
  - name: train
    num_bytes: 33732170
    num_examples: 6528
  download_size: 11085366
  dataset_size: 33732170
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
annotations_creators:
- crowdsourced
language:
- en
language_creators:
- crowdsourced
license:
- cc-by-4.0
multilinguality:
- monolingual
pretty_name: GitHub psf/requests repo issues with comments
size_categories:
- 1K<n<10K
source_datasets:
- original
tags:
- github
task_categories:
- text-classification
task_ids:
- multi-label-classification
---