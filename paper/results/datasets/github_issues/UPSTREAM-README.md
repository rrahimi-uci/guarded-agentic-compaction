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
    sequence: string
  - name: created_at
    dtype: timestamp[ns, tz=UTC]
  - name: updated_at
    dtype: timestamp[ns, tz=UTC]
  - name: closed_at
    dtype: timestamp[ns, tz=UTC]
  - name: author_association
    dtype: string
  - name: type
    dtype: float64
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
  splits:
  - name: train
    num_bytes: 47262287
    num_examples: 7540
  download_size: 12659096
  dataset_size: 47262287
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
license: apache-2.0
task_categories:
- text-classification
- text-generation
- question-answering
language:
- en
tags:
- github
pretty_name: HuggingFace Datasets Repository Issues
size_categories:
- 1K<n<10K
---


# HuggingFace Datasets Repository Issues

## Dataset Description

This dataset contains issues and pull requests from the [huggingface/datasets](https://github.com/huggingface/datasets) repository, collected via the GitHub API. Each entry includes comprehensive metadata about the issue/PR along with all associated comments, making it valuable for studying software development patterns, issue resolution processes, and community interactions in open-source projects.

### Dataset Summary

- **Repository**: huggingface/datasets
- **Total Issues/PRs**: 7,540
- **Date Collected**: June 13, 2025
- **Language**: English
- **License**: Apache 2.0

The dataset includes both open and closed issues/pull requests with their complete comment threads, providing rich context for understanding how software issues are discussed and resolved in a major open-source machine learning library.

### Supported Tasks and Leaderboards

This dataset can be used for various NLP and software engineering research tasks:

- **Text Classification**: Categorizing issues by type (bug, feature request, question, etc.)
- **Sentiment Analysis**: Analyzing the tone of issue discussions
- **Text Generation**: Generating responses to software issues
- **Question Answering**: Extracting answers from issue discussions
- **Software Engineering Research**: Studying issue resolution patterns, community interactions, and development workflows

### Languages

The dataset is primarily in English, as it contains issues from an English-speaking open-source community.

## Dataset Structure

### Data Instances

Each instance represents a single GitHub issue or pull request with the following structure:

```json
{
  "number": 7613,
  "title": "fix parallel push_to_hub in dataset_dict",
  "body": "Description of the issue...",
  "state": "open",
  "user": {
    "login": "username",
    "id": 12345,
    ...
  },
  "labels": [
    {
      "name": "bug",
      "color": "d73a4a",
      ...
    }
  ],
  "comments": [
    "First comment text...",
    "Second comment text...",
    ...
  ],
  "created_at": "2025-06-13T09:02:24Z",
  "updated_at": "2025-06-13T10:38:04Z",
  "pull_request": {
    "url": "https://api.github.com/repos/huggingface/datasets/pulls/7613",
    ...
  },
  ...
}
```

### Data Fields

- **number** (int64): Issue/PR number
- **title** (string): Title of the issue/PR
- **body** (string): Main description/content
- **state** (string): Current state (open/closed)
- **user** (struct): Information about the user who created the issue
- **labels** (list): Labels assigned to the issue
- **comments** (sequence): List of all comment texts
- **created_at** (timestamp): Creation timestamp
- **updated_at** (timestamp): Last update timestamp
- **closed_at** (timestamp): Closure timestamp (if closed)
- **pull_request** (struct): PR-specific metadata (if applicable)
- **assignee/assignees** (struct/list): Assigned users
- **milestone** (struct): Associated milestone information
- **reactions** (struct): Reaction counts (+1, -1, etc.)
- **author_association** (string): Relationship to repository (OWNER, CONTRIBUTOR, etc.)

### Data Splits

The dataset contains a single split:

- **train**: 7,540 issues/pull requests

## Dataset Creation

### Curation Rationale

This dataset was created to provide researchers and developers with real-world examples of software issue discussions and resolutions from a popular machine learning library. It can help understand:

- How technical issues are communicated and resolved
- Patterns in community interaction and support
- Evolution of software projects through issue tracking
- Natural language patterns in technical documentation

### Source Data

#### Initial Data Collection and Normalization

The data was collected using the GitHub API v4, specifically targeting the `huggingface/datasets` repository. The collection process:

1. **Issues Retrieval**: All issues and pull requests were fetched using paginated API calls
2. **Comments Collection**: For each issue/PR, all associated comments were retrieved
3. **Data Processing**: The raw JSON responses were processed and structured into a consistent format
4. **Timestamp Handling**: All timestamps were normalized to UTC format

#### Who are the source language producers?

The language producers are contributors to the HuggingFace datasets library, including:
- HuggingFace team members and maintainers
- Open-source contributors from the global developer community
- Users reporting bugs and requesting features
- Community members providing support and discussions

### Annotations

#### Annotation process

No additional annotations were added beyond the existing GitHub metadata (labels, assignees, milestones, etc.) that were already present in the repository.

#### Who are the annotators?

The repository maintainers and contributors who applied labels and other metadata during normal issue management processes.

### Personal and Sensitive Information

The dataset contains publicly available information from GitHub issues. While no intentionally sensitive information should be present, users should be aware that:

- GitHub usernames and profile information are included
- Some issues might contain system information, file paths, or configuration details
- Email addresses might appear in code snippets or error messages

## Considerations for Using the Data

### Social Impact of Dataset

This dataset can contribute positively to software engineering research and education by providing insights into collaborative development processes. However, users should consider:

- **Privacy**: Respect the public nature of the data and avoid any analysis that could harm individual contributors
- **Context**: Issues represent specific technical problems and may not generalize to all software projects
- **Bias**: The dataset reflects the specific community and practices of the HuggingFace ecosystem

### Discussion of Biases

Potential biases in the dataset include:

- **Language Bias**: Primarily English-language content
- **Domain Bias**: Focused on machine learning/data science library issues
- **Community Bias**: Reflects the practices and communication style of the HuggingFace community
- **Temporal Bias**: Represents issues from a specific time period in the project's evolution
- **Technical Bias**: May over-represent certain types of technical issues common in ML libraries

### Other Known Limitations

- The dataset represents a snapshot from June 13, 2025, and doesn't include subsequent updates
- Comment threads are included as lists but don't preserve detailed threading structure
- Some metadata fields may be incomplete for older issues
- The dataset doesn't include private repository discussions or communications

## Additional Information

### Dataset Curators

This dataset was curated by [Hélder Monteiro](https://huggingface.co/helmo) by extracting and processing public information from the HuggingFace datasets repository using the GitHub API.

### Licensing Information

This dataset is licensed under the Apache 2.0 License, consistent with the open-source nature of the original repository.

### Citation Information

```bibtex
@dataset{monteiro_huggingface_datasets_issues_2025,
  title={HuggingFace Datasets Repository Issues},
  author={Hélder Monteiro},
  year={2025},
  month={June},
  url={https://huggingface.co/datasets/helmo/github-issues},
  note={Issues and pull requests from huggingface/datasets repository collected and curated via GitHub API}
}
```

### Disclaimer

This dataset contains content created by the HuggingFace community members who opened issues, submitted pull requests, and participated in discussions on the datasets repository. While this dataset compilation is provided as it is, all original content belongs to the respective contributors.

For questions about this dataset or to report issues, please open an issue in the dataset repository or contact the dataset maintainers.