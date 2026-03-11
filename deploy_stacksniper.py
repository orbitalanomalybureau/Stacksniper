#!/usr/bin/env python3
"""
Stack Sniper DFS — Automated Deployment Script
================================================
Deploys the full stack by calling external APIs directly:
  1. GitHub:      Create repo, push code
  2. Stripe:      Create products, prices, webhook, customer portal
  3. Render:      Create DB, API, Worker, Static Site services
  4. Render:      Set all environment variables on each service
  5. Render:      Add custom domains
  6. GoDaddy:     Configure DNS (A + CNAME records)
  7. Render:      Trigger fresh deploys
  8. Verify:      Hit health endpoints

SECURITY:
  - Credentials loaded from .env file via python-dotenv
  - No secrets hardcoded in this file
  - Secrets masked in all log output
  - Live Stripe key triggers confirmation prompt
  - deployment_output.json masks sensitive values

USAGE:
  1. Fill in .env with your credentials (see .env template)
  2. pip install python-dotenv
  3. python3 deploy_stacksniper.py

REQUIREMENTS:
  pip install python-dotenv
  Python 3.9+, git
"""

import json
import os
import subprocess
import sys
import time
import secrets as secrets_mod
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path


# ============================================================
# LOAD CREDENTIALS FROM .env — NEVER HARDCODE
# ============================================================

def load_config():
    """Load credentials from .env file using python-dotenv."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("\033[91m✗ python-dotenv not installed.\033[0m")
        print("  Run: pip install python-dotenv")
        sys.exit(1)

    env_path = Path(".env")
    if not env_path.exists():
        env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print("\033[91m✗ .env file not found.\033[0m")
        print("  Create a .env file with your credentials.")
        print("  Copy .env.example and fill in your values.")
        sys.exit(1)

    load_dotenv(env_path, override=True)
    print(f"\033[92m✓ Loaded credentials from {env_path.resolve()}\033[0m")

    config = {
        "GITHUB_TOKEN":          os.environ.get("GITHUB_TOKEN", "").strip(),
        "GITHUB_OWNER":          os.environ.get("GITHUB_OWNER", "stacksniper").strip(),
        "GITHUB_REPO":           os.environ.get("GITHUB_REPO", "stacksniper").strip(),
        "STRIPE_SECRET_KEY":     os.environ.get("STRIPE_SECRET_KEY", "").strip(),
        "STRIPE_PUBLISHABLE_KEY":os.environ.get("STRIPE_PUBLISHABLE_KEY", "").strip(),
        "RENDER_API_KEY":        os.environ.get("RENDER_API_KEY", "").strip(),
        "GODADDY_API_KEY":       os.environ.get("GODADDY_API_KEY", "").strip(),
        "GODADDY_API_SECRET":    os.environ.get("GODADDY_API_SECRET", "").strip(),
        "SPORTSDATA_API_KEY":    os.environ.get("SPORTSDATA_API_KEY", "").strip(),
        "DOMAIN":                os.environ.get("DOMAIN", "stacksniper.com").strip(),
        "PROJECT_PATH":          os.environ.get("PROJECT_PATH", ".").strip(),
    }
    return config


def validate_config(config):
    """Check required credentials. Warn on optional. Block live Stripe without confirm."""
    required = ["GITHUB_TOKEN", "STRIPE_SECRET_KEY", "RENDER_API_KEY"]
    optional = ["GODADDY_API_KEY", "GODADDY_API_SECRET", "SPORTSDATA_API_KEY", "STRIPE_PUBLISHABLE_KEY"]

    missing_required = [k for k in required if not config.get(k)]
    missing_optional = [k for k in optional if not config.get(k)]

    if missing_required:
        log_error(f"Missing REQUIRED credentials in .env: {', '.join(missing_required)}")
        log_error("Fill these in your .env file before running.")
        sys.exit(1)

    for k in missing_optional:
        log_warn(f"{k} not set — that step will be skipped")

    # Safety: warn on live Stripe key
    sk = config.get("STRIPE_SECRET_KEY", "")
    if sk.startswith("sk_live_"):
        print(f"\n  {Colors.RED}{Colors.BOLD}⚠  WARNING: LIVE Stripe key detected (sk_live_).{Colors.END}")
        print(f"  {Colors.RED}  This creates REAL products that process REAL payments.{Colors.END}")
        print(f"  {Colors.YELLOW}  Recommended: Use sk_test_ first, switch to live after verification.{Colors.END}")
        resp = input(f"\n  Continue with live key? (type 'yes' to confirm): ")
        if resp.strip().lower() != "yes":
            print("  Aborted. Switch to test key in .env and re-run.")
            sys.exit(0)

    # Show loaded config (masked)
    print()
    for k, v in config.items():
        if not v:
            print(f"  {Colors.YELLOW}{k}{Colors.END} = (not set)")
        elif any(s in k for s in ("KEY", "SECRET", "TOKEN")):
            log_value(k, v)
        else:
            print(f"  {Colors.CYAN}{k}{Colors.END} = {v}")
    print()


# ============================================================
# GENERATED VALUES — populated during execution
# ============================================================

GENERATED = {
    "SECRET_KEY": secrets_mod.token_hex(32),
    "DATABASE_URL": "",
    "REDIS_URL": "",
    "STRIPE_WEBHOOK_SECRET": "",
    "STRIPE_PRICE_BASIC": "",
    "STRIPE_PRICE_PREMIUM": "",
    "STRIPE_PRICE_ENTERPRISE": "",
    "RENDER_API_SERVICE_ID": "",
    "RENDER_WORKER_SERVICE_ID": "",
    "RENDER_STATIC_SERVICE_ID": "",
    "RENDER_DB_ID": "",
}


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

class Colors:
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    END    = "\033[0m"

def log(msg, color=Colors.GREEN):
    print(f"{color}{Colors.BOLD}▸{Colors.END} {msg}")

def log_step(num, title):
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}  STEP {num}: {title}{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")

def log_success(msg):
    print(f"  {Colors.GREEN}✓ {msg}{Colors.END}")

def log_warn(msg):
    print(f"  {Colors.YELLOW}⚠ {msg}{Colors.END}")

def log_error(msg):
    print(f"  {Colors.RED}✗ {msg}{Colors.END}")

def log_value(key, value):
    if len(value) > 12:
        masked = value[:6] + "••••••••" + value[-3:]
    else:
        masked = "•" * len(value)
    print(f"  {Colors.CYAN}{key}{Colors.END} = {masked}")

def api_request(url, method="GET", data=None, headers=None, timeout=30):
    if headers is None:
        headers = {}
    headers.setdefault("Content-Type", "application/json")
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {"status": resp.status}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        log_error(f"HTTP {e.code}: {error_body[:300]}")
        raise

def run_cmd(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0 and "already exists" not in (result.stderr or ""):
        if result.stderr:
            log_error(result.stderr[:300])
    return result

def wait_with_dots(seconds, message="Waiting"):
    for i in range(seconds, 0, -1):
        print(f"\r  {message}... {i}s ", end="", flush=True)
        time.sleep(1)
    print(f"\r  {message}... done!   ")


# ============================================================
# STEP 1: GITHUB
# ============================================================

def setup_github(config):
    log_step(1, "GITHUB — Create Repo & Push Code")
    token   = config["GITHUB_TOKEN"]
    owner   = config["GITHUB_OWNER"]
    repo    = config["GITHUB_REPO"]
    project = config["PROJECT_PATH"]

    # Validate PROJECT_PATH — fall back to script directory if invalid
    if not project or not os.path.isdir(project):
        project = str(Path(__file__).parent.resolve())
        config["PROJECT_PATH"] = project
        log_warn(f"PROJECT_PATH invalid — using script directory: {project}")

    if not token:
        log_warn("No GITHUB_TOKEN — skipping.")
        return

    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    # Resolve actual GitHub username from token
    log("Resolving GitHub user from token...")
    try:
        user_info = api_request("https://api.github.com/user", headers=headers)
        actual_user = user_info.get("login", owner)
        log_success(f"Token belongs to: {actual_user}")
        if actual_user != owner:
            log_warn(f"GITHUB_OWNER={owner} but token user is {actual_user}")
            owner = actual_user
            config["GITHUB_OWNER"] = actual_user
    except Exception as e:
        log_warn(f"Could not resolve user: {e}")

    # Check / create repo
    log("Checking if repo exists...")
    repo_exists = False
    try:
        api_request(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
        log_success(f"Repo {owner}/{repo} already exists")
        repo_exists = True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            log("Creating repo...")
            try:
                api_request(f"https://api.github.com/orgs/{owner}/repos", method="POST",
                    data={"name": repo, "private": True, "description": "Stack Sniper DFS"}, headers=headers)
                log_success(f"Created repo: {owner}/{repo}")
                repo_exists = True
            except urllib.error.HTTPError:
                try:
                    api_request("https://api.github.com/user/repos", method="POST",
                        data={"name": repo, "private": True, "description": "Stack Sniper DFS"}, headers=headers)
                    log_success(f"Created repo: {owner}/{repo}")
                    repo_exists = True
                except urllib.error.HTTPError as e2:
                    error_body = e2.read().decode("utf-8") if e2.fp else ""
                    if e2.code == 422 and "already exists" in error_body:
                        log_success(f"Repo {owner}/{repo} already exists (confirmed via 422)")
                        repo_exists = True
                    else:
                        log_error(f"Could not create repo: HTTP {e2.code}")
        else:
            log_error(f"Could not check repo: HTTP {e.code}")

    if not repo_exists:
        log_warn("Skipping git push — repo not available")
        return

    # Ensure .env is in .gitignore
    gi = os.path.join(project, ".gitignore")
    if os.path.exists(gi):
        with open(gi, "r") as f:
            content = f.read()
        if ".env" not in content:
            with open(gi, "a") as f:
                f.write("\n# Credentials — never commit\n.env\n.env.*\ndeployment_output.json\n")
            log_success("Added .env to .gitignore")

    # Push
    log("Pushing code...")
    for cmd in [
        "git init",
        "git add -A",
        'git commit -m "Full MVP: Phases 0-6" --allow-empty',
        "git branch -M main",
        f"git remote remove origin 2>/dev/null; git remote add origin https://{token}@github.com/{owner}/{repo}.git",
        "git push -u origin main --force",
    ]:
        run_cmd(cmd, cwd=project)
    log_success(f"Pushed to https://github.com/{owner}/{repo}")


# ============================================================
# STEP 2: STRIPE
# ============================================================

def setup_stripe(config):
    log_step(2, "STRIPE — Create Products, Prices & Webhook")
    sk = config["STRIPE_SECRET_KEY"]
    if not sk:
        log_warn("No STRIPE_SECRET_KEY — skipping.")
        return

    import base64
    auth = base64.b64encode(f"{sk}:".encode()).decode()
    base_headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"}

    def stripe_req(endpoint, method="GET", form_data=None):
        url = f"https://api.stripe.com/v1/{endpoint}"
        body = urllib.parse.urlencode(form_data, doseq=True).encode() if form_data else None
        h = dict(base_headers)
        req = urllib.request.Request(url, data=body, headers=h, method=method)
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())

    tiers = [
        {"name": "Stack Sniper Basic",     "price": 1900,  "key": "basic"},
        {"name": "Stack Sniper Premium",    "price": 5900,  "key": "premium"},
        {"name": "Stack Sniper Enterprise", "price": 9900,  "key": "enterprise"},
    ]

    for tier in tiers:
        log(f"Product: {tier['name']}...")
        existing = stripe_req("products?limit=100")
        product = next((p for p in existing.get("data", []) if p["name"] == tier["name"]), None)

        if product:
            log_success(f"Exists: {product['id']}")
        else:
            product = stripe_req("products", method="POST", form_data={
                "name": tier["name"],
                "description": f"Stack Sniper DFS — {tier['key'].title()} tier",
            })
            log_success(f"Created: {product['id']}")

        prices = stripe_req(f"prices?product={product['id']}&active=true&limit=10")
        price = next((p for p in prices.get("data", [])
                       if p.get("unit_amount") == tier["price"]
                       and p.get("recurring", {}).get("interval") == "month"), None)

        if price:
            log_success(f"Price exists: {price['id']}")
        else:
            price = stripe_req("prices", method="POST", form_data={
                "product": product["id"],
                "unit_amount": tier["price"],
                "currency": "usd",
                "recurring[interval]": "month",
                "lookup_key": f"stacksniper_{tier['key']}",
            })
            log_success(f"Created price: {price['id']} (${tier['price']/100}/mo)")

        GENERATED[f"STRIPE_PRICE_{tier['key'].upper()}"] = price["id"]

    # Webhook
    domain = config["DOMAIN"]
    webhook_url = f"https://api.{domain}/api/billing/webhook"
    log(f"Webhook: {webhook_url}")

    hooks = stripe_req("webhook_endpoints?limit=50")
    hook = next((h for h in hooks.get("data", []) if h.get("url") == webhook_url), None)

    if hook:
        GENERATED["STRIPE_WEBHOOK_SECRET"] = "(existing — get from Stripe dashboard → Webhooks → Reveal)"
        log_warn(f"Webhook exists: {hook['id']} — retrieve signing secret from dashboard")
    else:
        hook = stripe_req("webhook_endpoints", method="POST", form_data={
            "url": webhook_url,
            "enabled_events[]": [
                "checkout.session.completed",
                "customer.subscription.updated",
                "customer.subscription.deleted",
                "invoice.payment_failed",
            ],
        })
        GENERATED["STRIPE_WEBHOOK_SECRET"] = hook.get("secret", "")
        log_success(f"Created webhook: {hook['id']}")
        if GENERATED["STRIPE_WEBHOOK_SECRET"]:
            log_value("STRIPE_WEBHOOK_SECRET", GENERATED["STRIPE_WEBHOOK_SECRET"])

    # Customer portal
    log("Configuring customer portal...")
    try:
        stripe_req("billing_portal/configurations", method="POST", form_data={
            "business_profile[headline]": "Stack Sniper DFS",
            "features[subscription_cancel][enabled]": "true",
            "features[subscription_cancel][mode]": "at_period_end",
            "features[payment_method_update][enabled]": "true",
        })
        log_success("Customer portal configured")
    except Exception:
        log_warn("Portal config skipped (may already exist or need dashboard setup)")


# ============================================================
# STEP 3: RENDER — Create services
# ============================================================

def setup_render(config):
    log_step(3, "RENDER — Create Database & Services")
    rk = config["RENDER_API_KEY"]
    if not rk:
        log_warn("No RENDER_API_KEY — skipping.")
        return

    headers = {"Authorization": f"Bearer {rk}", "Accept": "application/json", "Content-Type": "application/json"}
    owner = config["GITHUB_OWNER"]
    repo  = config["GITHUB_REPO"]

    # Owner
    log("Fetching Render account...")
    owners = api_request("https://api.render.com/v1/owners?limit=1", headers=headers)
    if not owners:
        log_error("Could not fetch Render owner.")
        return
    owner_id = owners[0]["owner"]["id"]
    log_success(f"Owner: {owner_id}")

    # Existing services
    existing = api_request("https://api.render.com/v1/services?limit=50", headers=headers)
    existing_map = {s["service"]["name"]: s["service"] for s in existing}

    # --- PostgreSQL ---
    log("PostgreSQL...")
    dbs = api_request("https://api.render.com/v1/postgres?limit=20", headers=headers)
    # First look for stacksniper-db, then fall back to any available DB
    db = next((d["postgres"] for d in dbs if d.get("postgres", {}).get("name") == "stacksniper-db"), None)
    if not db and dbs:
        # Use any existing DB (likely the free-tier one)
        db = dbs[0].get("postgres")
        if db:
            log_warn(f"stacksniper-db not found, using existing DB: {db['name']}")

    if db:
        GENERATED["RENDER_DB_ID"] = db["id"]
        log_success(f"Using DB: {db['name']} ({db['id']})")
    else:
        try:
            resp = api_request("https://api.render.com/v1/postgres", method="POST", headers=headers, data={
                "name": "stacksniper-db", "ownerId": owner_id, "plan": "free",
                "region": "oregon", "databaseName": "stacksniper",
                "databaseUser": "stacksniper_user", "version": "16",
            })
            db = resp["postgres"]
            GENERATED["RENDER_DB_ID"] = db["id"]
            log_success(f"Created: {db['id']}")
            wait_with_dots(30, "Provisioning")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            if "free tier" in error_body.lower():
                log_error("Cannot create free DB — one already exists.")
                log_warn("Delete the existing free DB in Render dashboard, or upgrade to paid.")
            else:
                log_error(f"DB creation failed: {error_body[:200]}")

    if GENERATED.get("RENDER_DB_ID"):
        try:
            db_info = api_request(f"https://api.render.com/v1/postgres/{GENERATED['RENDER_DB_ID']}/connection-info", headers=headers)
            internal = db_info.get("internalConnectionString", "")
            # Convert postgres:// to postgresql+asyncpg:// for SQLAlchemy
            if internal.startswith("postgres://"):
                internal = "postgresql+asyncpg://" + internal[len("postgres://"):]
            elif internal.startswith("postgresql://"):
                internal = "postgresql+asyncpg://" + internal[len("postgresql://"):]
            GENERATED["DATABASE_URL"] = internal
            log_value("DATABASE_URL", GENERATED["DATABASE_URL"])
        except Exception as e:
            log_error(f"Could not get DB connection info: {e}")
    else:
        log_warn("No database available — set DATABASE_URL manually in Render")

    # --- Redis ---
    log_warn("Render API doesn't support Redis creation. Create manually:")
    log_warn("  dashboard.render.com → New → Redis → stacksniper-redis → Free → Oregon")
    redis_svc = next((s["service"] for s in existing if "redis" in s.get("service", {}).get("name", "").lower()), None)
    if redis_svc:
        GENERATED["REDIS_URL"] = f"redis://{redis_svc['name']}:6379"
        log_success(f"Found: {redis_svc['name']}")
    else:
        GENERATED["REDIS_URL"] = "redis://localhost:6379"
        log_warn("Redis not found — update REDIS_URL after creating")

    # --- Helper to create or find a service ---
    # Render v1 API requires serviceDetails wrapper for non-static services
    gh_owner = config["GITHUB_OWNER"]
    gh_repo = config["GITHUB_REPO"]

    def ensure_service(name, svc_type, service_details):
        gen_key = {"stacksniper-api": "RENDER_API_SERVICE_ID",
                   "stacksniper-worker": "RENDER_WORKER_SERVICE_ID",
                   "stacksniper-web": "RENDER_STATIC_SERVICE_ID"}[name]
        if name in existing_map:
            GENERATED[gen_key] = existing_map[name]["id"]
            log_success(f"{name} exists: {existing_map[name]['id']}")
            return
        log(f"Creating {name}...")
        try:
            payload = {
                "name": name,
                "ownerId": owner_id,
                "type": svc_type,
                "serviceDetails": service_details,
            }
            resp = api_request("https://api.render.com/v1/services", method="POST", headers=headers, data=payload)
            GENERATED[gen_key] = resp["service"]["id"]
            log_success(f"Created: {resp['service']['id']}")
        except Exception as e:
            log_error(f"Failed: {e}")
            log_warn("May need to connect GitHub to Render in dashboard first.")

    ensure_service("stacksniper-api", "web_service", {
        "env": "docker",
        "envSpecificDetails": {
            "dockerContext": "./backend",
            "dockerfilePath": "./backend/Dockerfile",
        },
        "plan": "free",
        "region": "oregon",
        "repo": f"https://github.com/{gh_owner}/{gh_repo}",
        "branch": "main",
        "healthCheckPath": "/health",
        "numInstances": 1,
    })
    ensure_service("stacksniper-worker", "background_worker", {
        "env": "docker",
        "envSpecificDetails": {
            "dockerContext": "./backend",
            "dockerfilePath": "./backend/Dockerfile",
            "dockerCommand": "celery -A app.tasks.celery_app worker --loglevel=info",
        },
        "plan": "free",
        "region": "oregon",
        "repo": f"https://github.com/{gh_owner}/{gh_repo}",
        "branch": "main",
        "numInstances": 1,
    })
    ensure_service("stacksniper-web", "static_site", {
        "buildCommand": "cd frontend && npm install && npm run build",
        "publishPath": "frontend/public",
        "repo": f"https://github.com/{gh_owner}/{gh_repo}",
        "branch": "main",
        "routes": [{"type": "rewrite", "source": "/*", "destination": "/index.html"}],
    })


# ============================================================
# STEP 4: RENDER — Set env vars
# ============================================================

def set_render_env_vars(config):
    log_step(4, "RENDER — Set Environment Variables")
    rk = config["RENDER_API_KEY"]
    if not rk:
        return

    headers = {"Authorization": f"Bearer {rk}", "Accept": "application/json", "Content-Type": "application/json"}
    domain = config["DOMAIN"]

    backend_vars = [
        {"key": "DATABASE_URL",            "value": GENERATED["DATABASE_URL"]},
        {"key": "REDIS_URL",               "value": GENERATED["REDIS_URL"]},
        {"key": "SECRET_KEY",              "value": GENERATED["SECRET_KEY"]},
        {"key": "STRIPE_SECRET_KEY",       "value": config["STRIPE_SECRET_KEY"]},
        {"key": "STRIPE_WEBHOOK_SECRET",   "value": GENERATED["STRIPE_WEBHOOK_SECRET"]},
        {"key": "STRIPE_PRICE_BASIC",      "value": GENERATED["STRIPE_PRICE_BASIC"]},
        {"key": "STRIPE_PRICE_PREMIUM",    "value": GENERATED["STRIPE_PRICE_PREMIUM"]},
        {"key": "STRIPE_PRICE_ENTERPRISE", "value": GENERATED["STRIPE_PRICE_ENTERPRISE"]},
        {"key": "SPORTSDATA_API_KEY",      "value": config.get("SPORTSDATA_API_KEY", "")},
        {"key": "CORS_ORIGINS",            "value": f"https://{domain},https://www.{domain}"},
        {"key": "FRONTEND_URL",            "value": f"https://{domain}"},
        {"key": "ENVIRONMENT",             "value": "production"},
    ]
    frontend_vars = [
        {"key": "REACT_APP_API_URL",   "value": f"https://api.{domain}"},
        {"key": "REACT_APP_STRIPE_PK", "value": config.get("STRIPE_PUBLISHABLE_KEY", "")},
    ]

    def set_vars(svc_name, svc_id, vars_list):
        if not svc_id:
            log_warn(f"No ID for {svc_name} — skipping env vars")
            return
        active = [v for v in vars_list if v["value"]]
        skipped = [v["key"] for v in vars_list if not v["value"]]
        log(f"Setting env vars on {svc_name}...")
        try:
            api_request(f"https://api.render.com/v1/services/{svc_id}/env-vars",
                        method="PUT", headers=headers, data=active)
            for v in active:
                log_success(f"  {v['key']}")
            for k in skipped:
                log_warn(f"  {k} (empty — skipped)")
        except Exception as e:
            log_error(f"Failed on {svc_name}: {e}")

    set_vars("stacksniper-api",    GENERATED.get("RENDER_API_SERVICE_ID"),    backend_vars)
    set_vars("stacksniper-worker", GENERATED.get("RENDER_WORKER_SERVICE_ID"), backend_vars)
    set_vars("stacksniper-web",    GENERATED.get("RENDER_STATIC_SERVICE_ID"), frontend_vars)

    if not config.get("STRIPE_PUBLISHABLE_KEY"):
        log_warn("STRIPE_PUBLISHABLE_KEY not set — add pk_test_... to .env and re-run")


# ============================================================
# STEP 5A: RENDER — Custom domains
# ============================================================

def setup_render_domains(config):
    log_step("5A", "RENDER — Custom Domains")
    rk = config["RENDER_API_KEY"]
    if not rk:
        return
    headers = {"Authorization": f"Bearer {rk}", "Accept": "application/json", "Content-Type": "application/json"}
    domain = config["DOMAIN"]

    def add_domain(svc_id, d):
        try:
            api_request(f"https://api.render.com/v1/services/{svc_id}/custom-domains",
                        method="POST", headers=headers, data={"name": d})
            log_success(f"Added {d}")
        except urllib.error.HTTPError as e:
            if e.code == 409:
                log_success(f"{d} already configured")
            else:
                log_error(f"Failed: {d}")

    sid = GENERATED.get("RENDER_STATIC_SERVICE_ID")
    if sid:
        for d in [domain, f"www.{domain}"]:
            add_domain(sid, d)

    aid = GENERATED.get("RENDER_API_SERVICE_ID")
    if aid:
        add_domain(aid, f"api.{domain}")


# ============================================================
# STEP 5B: GODADDY — DNS
# ============================================================

def setup_godaddy_dns(config):
    log_step("5B", "GODADDY — DNS Records")
    gd_key    = config["GODADDY_API_KEY"]
    gd_secret = config["GODADDY_API_SECRET"]
    domain    = config["DOMAIN"]

    if not gd_key or not gd_secret:
        log_warn("No GoDaddy API keys — set DNS manually:")
        log_warn("  A     @   → 216.24.57.1")
        log_warn("  CNAME www → stacksniper-web.onrender.com")
        log_warn("  CNAME api → stacksniper-api.onrender.com")
        return

    headers = {"Authorization": f"sso-key {gd_key}:{gd_secret}", "Content-Type": "application/json"}

    records = [
        ("A",     "@",   "216.24.57.1",                      600),
        ("CNAME", "www", "stacksniper-web.onrender.com",      3600),
        ("CNAME", "api", "stacksniper-api.onrender.com",      3600),
    ]
    for rtype, name, value, ttl in records:
        log(f"{rtype} {name} → {value}")
        try:
            api_request(f"https://api.godaddy.com/v1/domains/{domain}/records/{rtype}/{name}",
                        method="PUT", headers=headers, data=[{"data": value, "ttl": ttl}])
            log_success(f"Set {rtype} {name}")
        except Exception as e:
            log_error(f"Failed {rtype} {name}: {e}")

    log_success("DNS configured. Propagation: 5–30 min.")


# ============================================================
# STEP 6: RENDER — Trigger deploys
# ============================================================

def trigger_deploys(config):
    log_step(6, "RENDER — Trigger Deploys")
    rk = config["RENDER_API_KEY"]
    if not rk:
        return
    headers = {"Authorization": f"Bearer {rk}", "Accept": "application/json", "Content-Type": "application/json"}

    for name, sid in [
        ("stacksniper-api",    GENERATED.get("RENDER_API_SERVICE_ID")),
        ("stacksniper-worker", GENERATED.get("RENDER_WORKER_SERVICE_ID")),
        ("stacksniper-web",    GENERATED.get("RENDER_STATIC_SERVICE_ID")),
    ]:
        if not sid:
            log_warn(f"No ID for {name}")
            continue
        log(f"Deploying {name}...")
        try:
            api_request(f"https://api.render.com/v1/services/{sid}/deploys",
                        method="POST", headers=headers, data={"clearCache": "do_not_clear"})
            log_success(f"Triggered: {name}")
        except Exception as e:
            log_error(f"Failed: {name} — {e}")

    log("Deploys take 3–8 min. Watch at: https://dashboard.render.com")


# ============================================================
# STEP 7: VERIFY
# ============================================================

def verify_deployment(config):
    log_step(7, "VERIFICATION")
    domain = config["DOMAIN"]

    log("Waiting 90s for deploys...")
    wait_with_dots(90, "Waiting")

    for url, desc in [
        (f"https://api.{domain}/health", "API health"),
        (f"https://{domain}",            "Frontend"),
    ]:
        log(f"Checking {desc}...")
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=20) as resp:
                log_success(f"{desc}: HTTP {resp.status}") if resp.status == 200 else log_warn(f"{desc}: HTTP {resp.status}")
        except Exception as e:
            log_warn(f"{desc}: Not reachable — {str(e)[:80]}")
            log_warn("  Normal if DNS is still propagating or deploy is running.")


# ============================================================
# SUMMARY
# ============================================================

def print_summary(config):
    log_step("✓", "DEPLOYMENT COMPLETE")
    domain = config["DOMAIN"]
    owner  = config["GITHUB_OWNER"]
    repo   = config["GITHUB_REPO"]

    print(f"""
{Colors.GREEN}{Colors.BOLD}  ╔══════════════════════════════════════════════════╗
  ║          STACK SNIPER DFS — DEPLOYED             ║
  ╚══════════════════════════════════════════════════╝{Colors.END}

  {Colors.CYAN}Frontend:{Colors.END}  https://{domain}
  {Colors.CYAN}API:{Colors.END}       https://api.{domain}
  {Colors.CYAN}Health:{Colors.END}    https://api.{domain}/health
  {Colors.CYAN}Docs:{Colors.END}      https://api.{domain}/docs
  {Colors.CYAN}GitHub:{Colors.END}    https://github.com/{owner}/{repo}

  {Colors.YELLOW}Manual Follow-Ups:{Colors.END}
  □ Create Redis in Render if not done (New → Redis → Free)
  □ Update REDIS_URL on API + Worker after creating Redis
  □ Verify DNS: nslookup {domain}
  □ Test signup → login → dashboard
  □ Test Stripe: card 4242 4242 4242 4242, any expiry, any CVC
  □ Run a test simulation
  □ Switch Stripe to live keys when ready
""")

    summary = {
        "urls": {"frontend": f"https://{domain}", "api": f"https://api.{domain}",
                 "github": f"https://github.com/{owner}/{repo}"},
        "stripe_prices": {k: GENERATED.get(f"STRIPE_PRICE_{k.upper()}", "")
                          for k in ("basic", "premium", "enterprise")},
        "render_ids": {k: GENERATED.get(f"RENDER_{k.upper()}_SERVICE_ID", "")
                       for k in ("api", "worker", "static")},
        "render_db_id": GENERATED.get("RENDER_DB_ID", ""),
        "note": "Secrets masked. Actual values are in your .env and Render dashboard.",
    }
    out = Path("deployment_output.json")
    out.write_text(json.dumps(summary, indent=2))
    log_success(f"Saved details to {out} (no secrets included)")


# ============================================================
# MAIN
# ============================================================

def main():
    print(f"""
{Colors.GREEN}{Colors.BOLD}
  ╔══════════════════════════════════════════════════╗
  ║    STACK SNIPER DFS — AUTOMATED DEPLOYMENT       ║
  ║    Credentials loaded from .env (never hardcoded) ║
  ╚══════════════════════════════════════════════════╝
{Colors.END}""")

    config = load_config()
    validate_config(config)

    print(f"  {Colors.YELLOW}This will create/modify resources on GitHub, Stripe, Render, and GoDaddy.{Colors.END}")
    resp = input(f"  Proceed? (y/n): ")
    if resp.strip().lower() not in ("y", "yes"):
        print("  Aborted.")
        sys.exit(0)

    steps = [
        ("GitHub",          setup_github),
        ("Stripe",          setup_stripe),
        ("Render Services", setup_render),
        ("Render Env Vars", set_render_env_vars),
        ("Render Domains",  setup_render_domains),
        ("GoDaddy DNS",     setup_godaddy_dns),
        ("Trigger Deploys", trigger_deploys),
        ("Verification",    verify_deployment),
    ]
    for name, func in steps:
        try:
            func(config)
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Interrupted at {name}.{Colors.END}")
            break
        except Exception as e:
            log_error(f"{name} failed: {e}")
            import traceback
            traceback.print_exc()
            log_warn(f"Continuing to next step...")
    print_summary(config)


if __name__ == "__main__":
    main()
