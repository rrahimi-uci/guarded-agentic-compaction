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
    sequence: string
  - name: state
    dtype: string
  - name: locked
    dtype: bool
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
    dtype: timestamp[ns, tz=UTC]
  - name: updated_at
    dtype: timestamp[ns, tz=UTC]
  - name: closed_at
    dtype: timestamp[ns, tz=UTC]
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
  - name: author_association
    dtype: string
  - name: type
    struct:
    - name: color
      dtype: string
    - name: created_at
      dtype: string
    - name: description
      dtype: string
    - name: id
      dtype: int64
    - name: is_enabled
      dtype: bool
    - name: name
      dtype: string
    - name: node_id
      dtype: string
    - name: updated_at
      dtype: string
  - name: active_lock_reason
    dtype: float64
  - name: draft
    dtype: float64
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
    dtype: float64
  - name: state_reason
    dtype: string
  - name: sub_issues_summary
    struct:
    - name: completed
      dtype: int64
    - name: percent_completed
      dtype: int64
    - name: total
      dtype: int64
  - name: issue_dependencies_summary
    struct:
    - name: blocked_by
      dtype: int64
    - name: blocking
      dtype: int64
    - name: total_blocked_by
      dtype: int64
    - name: total_blocking
      dtype: int64
  - name: pinned_comment
    dtype: float64
  - name: parent_issue_url
    dtype: string
  splits:
  - name: train
    num_bytes: 40887888.735151514
    num_examples: 9609
  download_size: 9622959
  dataset_size: 40887888.735151514
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
---
