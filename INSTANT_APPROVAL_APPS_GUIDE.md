# ConnectorHub: Instant-Approval Apps & Credentials Guide

This guide contains complete, copy-paste setup details (**Redirect URIs, Scopes, Developer Portal Links, and Step-by-Step instructions**) for third-party platforms in ConnectorHub that offer **immediate approval**.

> [!NOTE]
> **What is an "Instant-Approval" Provider?**
> Unlike Google, Meta, or Apple which require weeks of business verification and video demonstration reviews, the platforms in this guide:
> 1. Grant immediate access in **Development / Testing / Personal** mode.
> 2. Generate live OAuth credentials (`Client ID` & `Client Secret`) or direct personal tokens in under 60 seconds.
> 3. Allow immediate execution of real API actions with zero delay.

---

## 1. Quick Reference Table

| Provider | Category | Actions | Auth Method | Developer Portal | Approval Time |
| :--- | :--- | :---: | :--- | :--- | :---: |
| **Notion** | Productivity | **23** | OAuth 2.0 / Token | [Notion Developers](https://www.notion.so/my-integrations) | **Instant** |
| **Spotify** | Media & Audio | **21** | OAuth 2.0 | [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) | **Instant** |
| **Discord** | Communication | **17** | OAuth 2.0 / Bot Token | [Discord Developer Portal](https://discord.com/developers/applications) | **Instant** |
| **Dropbox** | Storage | **24** | OAuth 2.0 / Token | [Dropbox App Console](https://www.dropbox.com/developers/apps) | **Instant** |
| **Miro** | Collaboration | **12** | OAuth 2.0 | [Miro Developer Portal](https://developers.miro.com/) | **Instant** |
| **Canva** | Design & Media | **13** | OAuth 2.0 | [Canva Developers](https://www.canva.com/developers/) | **Instant** |
| **Telegram** | Communication | **14** | Bot Token | Telegram `@BotFather` | **30 Seconds** |
| **Trello** | Project Management | **24** | API Key & Token | [trello.com/app-key](https://trello.com/app-key) | **1 Click** |
| **Figma** | Design & UI | **13** | Personal Access Token | Figma Settings > Account | **5 Seconds** |
| **Coda** | Docs & DB | **12** | API Token | [coda.io/account](https://coda.io/account) | **1 Click** |
| **Cal.com** | Scheduling | **11** | API Key | Cal.com Settings > Developer | **1 Click** |
| **Jotform** | Forms & Surveys | **7** | API Key | Jotform Settings > API | **1 Click** |
| **Bitly** | Link Management | **6** | Access Token | Bitly Settings > Developer | **1 Click** |
| **Vercel** | Cloud & Hosting | **12** | Access Token | Vercel Settings > Tokens | **1 Click** |
| **Docker Hub** | Containers | **14** | Access Token | Docker Hub Settings > Security | **1 Click** |
| **GroqCloud** | AI & LLMs | **4** | API Key | [console.groq.com](https://console.groq.com/keys) | **Instant** |
| **Perplexity** | AI Search | **4** | API Key | [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api) | **Instant** |
| **Anthropic** | AI & LLMs | **5** | API Key | [console.anthropic.com](https://console.anthropic.com/settings/keys) | **Instant** |
| **Resend** | Email Delivery | **9** | API Key | [resend.com/api-keys](https://resend.com/api-keys) | **Instant** |
| **Postmark** | Transactional Email | **12** | Server Token | [account.postmarkapp.com](https://account.postmarkapp.com/) | **Instant** |

---

## 2. Global Redirect URI Pattern

For any OAuth 2.0 provider, the callback endpoint on ConnectorHub follows this exact format:

* **Production (Hosted)**:
  ```text
  https://connector.suparagent.ai/api/oauth/<service>/callback
  ```
* **Local Development**:
  ```text
  http://localhost:8000/api/oauth/<service>/callback
  ```

---

## 3. Tier 1: Instant OAuth 2.0 Providers (Full Web Flow)

### 3.1 Notion
* **Service ID**: `notion`
* **Actions Available**: **23 actions** (Pages, Databases, Blocks, Users, Comments)
* **Developer Portal**: [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
* **Authorized Redirect URI**:
  ```text
  https://connector.suparagent.ai/api/oauth/notion/callback
  ```
* **Required Capabilities**:
  * Under **Capabilities**, enable:
    * `Read content`
    * `Update content`
    * `Insert content`
    * `Read user information including email addresses`
* **Setup Steps**:
  1. Go to [Notion Integrations](https://www.notion.so/my-integrations) and click **+ New integration**.
  2. Select your associated workspace, name it (e.g. `ConnectorHub`), and set the integration type to **Public** (or **Internal**).
  3. Under **Redirect URIs**, add `https://connector.suparagent.ai/api/oauth/notion/callback`.
  4. Under **Secrets**, copy your **OAuth Client ID** and **OAuth Client Secret**.
  5. In ConnectorHub, open **Notion**, select **Custom OAuth**, paste both values, and click **Save & Connect**.
  > [!TIP]
  > **Even Faster Setup (Internal Token)**: If you select **Internal integration**, Notion generates an Internal Integration Secret starting with `secret_...`. In ConnectorHub, choose the **Personal Token** tab and paste it directly!

---

### 3.2 Spotify
* **Service ID**: `spotify`
* **Actions Available**: **21 actions** (Playlists, Playback Control, User Profile, Saved Tracks)
* **Developer Portal**: [https://developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
* **Authorized Redirect URI**:
  ```text
  https://connector.suparagent.ai/api/oauth/spotify/callback
  ```
* **Recommended Scopes**:
  ```text
  user-read-private user-read-email user-read-playback-state user-modify-playback-state playlist-read-private playlist-modify-public
  ```
* **Setup Steps**:
  1. Open [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and sign in.
  2. Click **Create App**:
     * **App Name**: `ConnectorHub`
     * **App Description**: `ConnectorHub Agent Integration`
     * **Redirect URIs**: `https://connector.suparagent.ai/api/oauth/spotify/callback`
     * Check the **Developer Terms of Service** agreement and click **Save**.
  3. Click **Settings** to access your **Client ID**, then click **View client secret** to copy your **Client Secret**.
  4. In ConnectorHub, open **Spotify**, select **Custom OAuth**, paste both values, and click **Save & Connect**.

---

### 3.3 Discord
* **Service ID**: `discord`
* **Actions Available**: **17 actions** (Channels, Messages, Guilds, Members, Roles, Webhooks)
* **Developer Portal**: [https://discord.com/developers/applications](https://discord.com/developers/applications)
* **Authorized Redirect URI**:
  ```text
  https://connector.suparagent.ai/api/oauth/discord/callback
  ```
* **Default Scopes**:
  ```text
  identify email guilds guilds.members.read connections bot
  ```
* **Setup Steps**:
  1. Open [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**.
  2. Give it a name (e.g. `ConnectorHub`) and agree to the Developer Policy.
  3. Navigate to **OAuth2 > General**:
     * Under **Redirects**, click **Add Redirect** and paste:
       ```text
       https://connector.suparagent.ai/api/oauth/discord/callback
       ```
     * Click **Save Changes**.
     * Copy the **Client ID** and click **Reset Secret** to copy your **Client Secret**.
  4. In ConnectorHub, open **Discord**, select **Custom OAuth**, paste both values, and click **Save & Connect**.
  > [!TIP]
  > **Bot Mode**: To control Discord bot messages, open the **Bot** tab in Discord, click **Reset Token**, copy the bot token, and paste it under the **Bot Token** tab in ConnectorHub!

---

### 3.4 Dropbox
* **Service ID**: `dropbox`
* **Actions Available**: **24 actions** (Upload, Download, Share Links, List Folders, Metadata)
* **Developer Portal**: [https://www.dropbox.com/developers/apps](https://www.dropbox.com/developers/apps)
* **Authorized Redirect URI**:
  ```text
  https://connector.suparagent.ai/api/oauth/dropbox/callback
  ```
* **Required Scopes / Permissions**:
  Under the **Permissions** tab, enable:
  * `account_info.read`
  * `files.metadata.read`
  * `files.metadata.write`
  * `files.content.read`
  * `files.content.write`
  * `sharing.read`
  * Click **Submit** at the bottom of the page to apply changes.
* **Setup Steps**:
  1. Open [Dropbox App Console](https://www.dropbox.com/developers/apps) and click **Create app**.
  2. Choose **Scoped access** and select **Full Dropbox**.
  3. Under the **Settings** tab:
     * In the **OAuth 2 > Redirect URIs** field, add:
       ```text
       https://connector.suparagent.ai/api/oauth/dropbox/callback
       ```
     * Copy your **App key** (`Client ID`) and **App secret** (`Client Secret`).
  4. In ConnectorHub, open **Dropbox**, paste both into **Custom OAuth**, and click **Save & Connect**.

---

### 3.5 Miro
* **Service ID**: `miro`
* **Actions Available**: **12 actions** (Boards, Sticky Notes, Shapes, Connectors, Items)
* **Developer Portal**: [https://developers.miro.com/](https://developers.miro.com/)
* **Authorized Redirect URI**:
  ```text
  https://connector.suparagent.ai/api/oauth/miro/callback
  ```
* **Scopes**:
  ```text
  boards:read boards:write
  ```
* **Setup Steps**:
  1. Open [Miro Developer Portal](https://developers.miro.com/) or click your avatar in Miro > **Settings > Your apps**.
  2. Click **Create new app**.
  3. In **Redirect URI for OAuth2.0**, paste:
     ```text
     https://connector.suparagent.ai/api/oauth/miro/callback
     ```
  4. Under **Permissions**, check `boards:read` and `boards:write`.
  5. Copy your **Client ID** and **Client Secret**.
  6. In ConnectorHub, open **Miro**, paste them into **Custom OAuth**, and connect.

---

### 3.6 Canva
* **Service ID**: `canva`
* **Actions Available**: **13 actions** (Designs, Exports, Assets, Folders, User Profiles)
* **Developer Portal**: [https://www.canva.com/developers/](https://www.canva.com/developers/)
* **Authorized Redirect URI**:
  ```text
  https://connector.suparagent.ai/api/oauth/canva/callback
  ```
* **Scopes**:
  ```text
  design:meta:read design:content:read design:content:write asset:read asset:write folder:read folder:write profile:read
  ```
* **Setup Steps**:
  1. Open [Canva Developers](https://www.canva.com/developers/) and click **Your integrations**.
  2. Click **Create an integration**.
  3. Under **Authentication**:
     * Set redirect URL to `https://connector.suparagent.ai/api/oauth/canva/callback`.
     * Copy the generated **Client ID** and **Client Secret**.
  4. Connect via **Custom OAuth** in ConnectorHub.

---

## 4. Tier 2: 1-Click Personal Tokens & API Keys (Zero-Wait Setup)

These providers require no OAuth redirect setup at all. You generate an authorized token directly from your account settings in seconds:

### 4.1 Telegram (Fastest Bot Setup — 30 Seconds)
* **Service ID**: `telegram`
* **Actions Available**: **14 actions** (Send Messages, Photos, Documents, Pin, Polls)
* **How to get token**:
  1. Open the Telegram app and search for `@BotFather` (verified blue checkmark).
  2. Send `/newbot`.
  3. Choose a display name, then choose a username ending in `bot` (e.g. `supar_connector_bot`).
  4. `@BotFather` instantly outputs your HTTP Bot Token:
     ```text
     123456789:ABCdefGhIJKlmNoPQRstuVWXyz
     ```
  5. In ConnectorHub, open **Telegram**, paste the token, and click **Connect**.

### 4.2 Trello (1-Click Key & Token)
* **Service ID**: `trello`
* **Actions Available**: **24 actions** (Cards, Boards, Lists, Checklists, Comments)
* **How to get token**:
  1. Go to [trello.com/app-key](https://trello.com/app-key) while signed in.
  2. Copy your **API Key**.
  3. Right under the Key box, click the hyperlink labeled **"Token"**.
  4. Click **Allow** on the permission screen and copy the 64-character token.
  5. Paste both into ConnectorHub.

### 4.3 Figma (Instant Personal Access Token)
* **Service ID**: `figma`
* **Actions Available**: **13 actions** (Files, Nodes, Comments, Projects, Images)
* **How to get token**:
  1. Open Figma and click your avatar (top-left) > **Settings**.
  2. Under the **Account** tab, scroll to **Personal access tokens**.
  3. Click **Generate new token**, name it `ConnectorHub`, and check read/write scopes.
  4. Copy the token starting with `figd_...` and connect in ConnectorHub.

### 4.4 Coda
* **Service ID**: `coda`
* **Actions Available**: **12 actions** (Docs, Tables, Rows, Formulas, Controls)
* **How to get token**:
  1. Open [coda.io/account](https://coda.io/account).
  2. Scroll to **API Settings** and click **Generate API token**.
  3. Paste the token into ConnectorHub.

### 4.5 Cal.com
* **Service ID**: `cal`
* **Actions Available**: **11 actions** (Bookings, Event Types, Availability, Schedules)
* **How to get token**:
  1. In Cal.com, go to **Settings > Developer > API Keys**.
  2. Click **+ Add** to generate an instant key.
  3. Paste into ConnectorHub.

### 4.6 Jotform
* **Service ID**: `jotform`
* **Actions Available**: **7 actions** (Forms, Questions, Submissions, Reports)
* **How to get token**:
  1. Go to **Settings > API > Create New Key**.
  2. Set permissions to **Full Access** and paste into ConnectorHub.

### 4.7 Bitly
* **Service ID**: `bitly`
* **Actions Available**: **6 actions** (Shorten Links, QR Codes, Bitlink Metrics, Groups)
* **How to get token**:
  1. In Bitly, click **Settings > Developer Settings > Generic Access Token**.
  2. Re-enter your password to generate a permanent token.
  3. Paste into ConnectorHub.

---

## 5. Tier 3: Instant AI & LLM Providers

| Provider | Service ID | Actions | Portal Link | How to get Key |
| :--- | :--- | :---: | :--- | :--- |
| **GroqCloud** | `groqcloud` | **4** | [console.groq.com](https://console.groq.com/keys) | Click **Create API Key**; copy instant `gsk_...` key. |
| **Perplexity** | `perplexity` | **4** | [perplexity.ai](https://www.perplexity.ai/settings/api) | Under API settings, generate an instant `pplx-...` key. |
| **Anthropic** | `anthropic` | **5** | [console.anthropic.com](https://console.anthropic.com/settings/keys) | Click **Create Key**; copy `sk-ant-...` key. |
| **Firecrawl** | `firecrawl` | **4** | [firecrawl.dev](https://www.firecrawl.dev/app/api-keys) | Copy your default `fc-...` API key from the dashboard. |
| **Together AI** | `together_ai` | **5** | [api.together.ai](https://api.together.ai/settings/api-keys) | Copy your account API key in 1 click. |
| **Cohere** | `cohere` | **6** | [dashboard.cohere.com](https://dashboard.cohere.com/api-keys) | Copy your trial/production API key. |

---

## 6. Tier 4: Developer DevOps & Email Delivery

### 6.1 Resend
* **Service ID**: `resend`
* **Actions Available**: **9 actions** (Send Email, Batch, Domains, API Keys)
* **Key Generation**:
  1. Go to [resend.com/api-keys](https://resend.com/api-keys).
  2. Click **Create API Key**, select **Full Access**, and copy `re_...`.

### 6.2 Postmark
* **Service ID**: `postmark`
* **Actions Available**: **12 actions** (Transactional Email, Templates, Message Streams)
* **Key Generation**:
  1. Log in to [Postmark](https://account.postmarkapp.com/) and open any server.
  2. Click the **API Tokens** tab and copy your **Server API Token**.

### 6.3 Vercel
* **Service ID**: `vercel`
* **Actions Available**: **12 actions** (Deployments, Projects, Domains, DNS)
* **Token Generation**:
  1. Go to **Account Settings > Tokens**.
  2. Click **Create**, choose scope, and copy the personal token.

### 6.4 Docker Hub
* **Service ID**: `docker_hub`
* **Actions Available**: **14 actions** (Repositories, Tags, Namespaces, Builds)
* **Token Generation**:
  1. Go to **Account Settings > Security > Access Tokens**.
  2. Click **New Access Token** with read/write access.
