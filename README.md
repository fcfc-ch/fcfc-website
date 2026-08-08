# fcfc.ch — business card site with AI-refreshed news

A one-page site for FC Finance Consulting GmbH, with a "Trade desk notes"
section that refreshes itself daily via a scheduled GitHub Action that calls
the Claude API.

No server to run, no ongoing maintenance beyond occasionally editing copy.
Everything below is a one-time setup.

---

## What's in this folder

```
index.html                        the page
assets/style.css                  all styling
assets/script.js                  reads news.json and renders it
assets/logo.png                   your company logo
news.json                         the news data (overwritten automatically)
CNAME                             tells GitHub Pages to serve www.fcfc.ch
scripts/update_news.py            calls Claude API, writes news.json
scripts/requirements.txt          Python dependency (anthropic SDK)
.github/workflows/update-news.yml the daily automation
```

---

## Step 1 — Create the GitHub repository

1. Go to https://github.com and sign in (or create a free account).
2. Click **New repository**. Name it e.g. `fcfc-website`. Keep it **Public**
   (GitHub Pages' free tier needs a public repo, unless you're on a paid plan).
3. Don't initialize with a README — you already have one.
4. On the new repo's page, click **uploading an existing file** and drag in
   every file/folder from this project, keeping the folder structure exactly
   as it is (including the `.github` folder — GitHub sometimes hides
   dotfolders in the upload UI; if `.github/workflows/update-news.yml`
   doesn't show up after upload, use **Add file → Create new file** and
   paste its contents in at that exact path).
5. Commit the files to the `main` branch.

## Step 2 — Turn on GitHub Pages

1. In the repo, go to **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **Deploy from a branch**.
3. Branch: `main`, folder: `/ (root)`. Save.
4. GitHub will build and give you a temporary URL like
   `https://<your-username>.github.io/fcfc-website/` — check it loads before
   moving on to the custom domain.

## Step 3 — Add your Claude API key as a secret

1. Get an API key from the Claude Platform console (console.claude.com →
   API Keys), if you don't already have one.
2. In the repo, go to **Settings → Secrets and variables → Actions**.
3. Click **New repository secret**.
   - Name: `ANTHROPIC_API_KEY`
   - Value: your key
4. Save. This lets the automation call Claude without the key ever
   appearing in your code or being visible to visitors.

## Step 4 — Point fcfc.ch at GitHub Pages

At your domain registrar (wherever fcfc.ch is registered), edit the DNS
records:

**For the apex domain (`fcfc.ch`)** — add four A records, all pointing to:
```
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```

**For `www.fcfc.ch`** — add a CNAME record pointing to:
```
<your-username>.github.io
```

DNS changes can take anywhere from a few minutes to a few hours to propagate.

## Step 5 — Set the custom domain in GitHub

1. Back in **Settings → Pages**, under **Custom domain**, enter `www.fcfc.ch`
   and save (this confirms the `CNAME` file already in the repo).
2. Once DNS has propagated, tick **Enforce HTTPS** — GitHub issues a free
   SSL certificate automatically.

## Step 6 — Test the news automation manually

1. Go to the **Actions** tab → **Update trade desk notes** → **Run workflow**
   (this uses the `workflow_dispatch` trigger, so you don't have to wait for
   the daily schedule).
2. Once it finishes (green check), open your site and refresh — the "Trade
   desk notes" section should show real, current items instead of the
   placeholder text.
3. From here it runs automatically every day at 05:00 UTC — edit the `cron`
   line in `.github/workflows/update-news.yml` if you want a different time
   or frequency.

## Step 7 — Personalize the content

Open `index.html` and update:
- `info@fcfc.ch` and the LinkedIn link in the footer
- Any wording in the hero, services, or about sections

No build step — just edit and commit; the live site updates within a minute
or two of the push.

---

## Cost

Each automated run makes one Claude API call with a handful of web searches.
At daily frequency this is a small, predictable cost (a few cents to low
dollars a month depending on usage) — check current pricing at
https://docs.claude.com/en/docs/about-claude/pricing before relying on an
exact figure.

## If something breaks

- **News section stuck on "Loading…" or "unavailable"** — open the browser
  console (right-click → Inspect → Console) for the exact error; usually
  either `news.json` failed to fetch (path issue) or is malformed JSON.
- **Action fails in the Actions tab** — click into the failed run's logs;
  the most common causes are a missing/incorrect `ANTHROPIC_API_KEY` secret
  or the model returning text that isn't valid JSON (the script tries to
  extract the JSON array regardless of stray text, but very unusual replies
  can still fail — re-running usually resolves it).
- **Custom domain not working** — double-check the DNS records above and
  give propagation a few hours; https://dnschecker.org can confirm what's
  actually live.
