# Social Integrations — implementation contract

This module is a verified-integration backlog and safety contract, not a claim that accounts are connected or publishing works today.

## Platform status

All entries begin as `documented_not_connected`. A platform becomes `connected` only after a real OAuth/token flow succeeds for the user's account and a read-only verification call succeeds. Publishing becomes `publish_enabled` only after the required scopes, app review/audit and a test publication are confirmed.

| Platform | Official API family | Authentication / access gate | Current repo status |
|---|---|---|---|
| YouTube | YouTube Data API v3 | OAuth 2.0 for uploads/private channel data; enable API and configure OAuth client | documented_not_connected |
| Instagram | Instagram Platform / Graph API | Professional account, Meta app, account authorization and applicable permissions/review | documented_not_connected |
| Facebook Pages | Graph API / Pages publishing | Page authorization and permissions; personal-profile publishing is not assumed | documented_not_connected |
| Threads | Threads API | Meta app, OAuth and publishing permission | documented_not_connected |
| TikTok | Content Posting API | Developer app, OAuth scopes and audit for public posting where required | documented_not_connected |
| X | X API | Developer access; pricing/credits and endpoint access must be checked before use | documented_not_connected |
| LinkedIn | Posts API / Community Management | OAuth; organization access may require product approval and Page role | documented_not_connected |
| Pinterest | Pinterest API v5 | OAuth and applicable access tier | documented_not_connected |
| Bluesky | AT Protocol | Account authentication/app password or supported OAuth; respect service limits | documented_not_connected |
| Mastodon | Mastodon API | Instance-specific app registration and OAuth token | documented_not_connected |

## Non-negotiable publishing flow

1. User explicitly connects the account through its official OAuth flow. Never request or store account passwords.
2. Store access/refresh tokens only in an encrypted secret store. Never commit tokens, client secrets, or raw credentials.
3. Verify account identity and granted scopes; persist the provider account ID, token expiry and granted scopes.
4. Validate media format, duration, size, caption length and visibility options against the current official endpoint documentation.
5. Create a draft and show the exact platform, account, media, caption and visibility to the user.
6. Require explicit user approval before publishing. A scheduling request may authorize the specific scheduled post, but not unrelated posts.
7. Use an idempotency key or provider upload/session ID where supported. After an ambiguous timeout, reconcile remote status before retrying to avoid duplicate posts.
8. Persist the remote post ID, URL, status, timestamps and sanitized error details.
9. Read analytics only for scopes and metrics the account actually grants. Respect platform rate limits and retention policies.

## Current implementation boundary

This repository does not yet contain complete OAuth callback handlers or platform-specific upload/publishing adapters. These require registered app credentials, exact redirect URIs, user consent, platform permissions and sometimes external review. Therefore no social account is connected and no post can be published from this module yet.

## Official developer documentation

- YouTube authorization: https://developers.google.com/youtube/data/guides/authentication
- YouTube uploads: https://developers.google.com/youtube/v3/docs/videos/insert
- Instagram Platform: https://developers.facebook.com/docs/instagram-platform/
- Facebook Graph API: https://developers.facebook.com/docs/graph-api/
- Threads API: https://developers.facebook.com/docs/threads/
- TikTok Content Posting API: https://developers.tiktok.com/products/content-posting-api/
- X API: https://docs.x.com/
- LinkedIn APIs: https://learn.microsoft.com/en-us/linkedin/
- Pinterest API: https://developers.pinterest.com/docs/
- Bluesky AT Protocol: https://docs.bsky.app/
- Mastodon API: https://docs.joinmastodon.org/api/

Always re-check current official requirements at implementation time. Do not infer that an API is free, available to every account, or approved for public publishing.
