# Fork feature index

The tables below exist to connect fork names with upstream code names. Add a
row to the matching table when you add the change. A feature adds something
upstream Zulip doesn't offer. An improvement changes something upstream already
offers.

## Features

| Feature                  | Code                                                                                      |
| ------------------------ | ----------------------------------------------------------------------------------------- |
| hide upload thumbnails   | `miatsuco_inline_upload_preview`                                                          |
| personal hide previews   | `miatsuco_web_show_upload_thumbnails`, `miatsuco_collapsed_media`                         |
| org DM restrictions      | `direct_message_self_authorize_group`                                                     |
| personal DM restrictions | `miatsuco_restrict_dms_to_authorizers`, `miatsuco_dm_authorizer_display`                  |
| email visibility policy  | `email_address_visibility_max`, `email_address_visibility_min`, `email_visibility_policy` |
| retain topics            | `miatsuco_retain_topics`                                                                  |
| pinned topic             | `miatsuco_pinned_topic`, `miatsuco_pinned_topic_name`                                     |
| channel email posting    | `miatsuco_allow_user_email_posting`, `miatsuco_channel_email`                             |

## Improvements

| Improvement                  | Code                                                                                                                      |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| inline embeds                | `miatsuco_inline_embed`, `miatsuco_inline_video`, `miatsuco_oembed_providers`                                             |
| bulk remediation             | `bulk_remediation`, `bulk_remediation_ui`                                                                                 |
| two-pole slider              | `two_pole_slider`, `nouislider`                                                                                           |
| message modernization        | `miatsuco_click_handlers`                                                                                                 |
| social cards                 | `miatsuco_message_card_embed`, `miatsuco_fxembed`                                                                         |
| rerender embeds              | `miatsuco_rerender_embeds`                                                                                                |
| channel retention permission | `message_retention_days`                                                                                                  |
| more permission options      | `miatsuco_can_manage_user_activation_group`, `miatsuco_can_change_user_roles_group`, `miatsuco_can_edit_user_names_group` |

## Feature levels

The feature level goes up by one in each PR that changes the fork's API. It
works like upstream's feature level, so the [Zulip API
changelog](https://zulip.com/api/changelog) explains how clients use it. Add a
row here when you raise it.

| Level | Change                                                                          |
| ----- | ------------------------------------------------------------------------------- |
| 1     | `miatsuco_version` and `miatsuco_feature_level` are advertised                  |
| 2     | hide upload thumbnails and personal hide previews settings                      |
| 3     | org DM restrictions and personal DM restrictions settings                       |
| 4     | email visibility policy settings and endpoints                                  |
| 5     | more permission options, retain topics, pinned topic, and channel email posting |
