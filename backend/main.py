import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from tortoise.contrib.fastapi import register_tortoise

from tortoise_conf import TORTOISE_ORM
from routes.auth import router as auth_router
from routes.projects import router as projects_router
from routes.plans import router as plans_router
from models import Plan

app = FastAPI(
    title="HTML Plan Service",
    version="0.1.0",
    description="Service to store and serve HTML plans",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(plans_router, prefix="/api/plans", tags=["plans"])


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Plan Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f0f0f; color: #e0e0e0; min-height: 100vh; }
  .header { background: #1a1a2e; border-bottom: 1px solid #333; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; }
  .header h1 { font-size: 18px; color: #fff; }
  .header .email { color: #888; font-size: 13px; }
  .header button { background: #333; color: #ccc; border: 1px solid #555; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }
  .header button:hover { background: #444; }
  .container { max-width: 900px; margin: 0 auto; padding: 24px; }
  .login-box { max-width: 400px; margin: 80px auto; text-align: center; }
  .login-box h2 { margin-bottom: 16px; font-size: 20px; }
  .login-box input { width: 100%; padding: 10px 14px; background: #1a1a2e; border: 1px solid #333; color: #fff; border-radius: 8px; font-size: 14px; margin-bottom: 12px; }
  .login-box button { width: 100%; padding: 10px; background: #6c5ce7; color: #fff; border: none; border-radius: 8px; font-size: 14px; cursor: pointer; font-weight: 600; }
  .login-box button:hover { background: #5a4bd1; }
  .login-box .hint { color: #666; font-size: 12px; margin-top: 8px; }
  .stats { display: flex; gap: 16px; margin-bottom: 24px; }
  .stat { background: #1a1a2e; border: 1px solid #333; border-radius: 10px; padding: 16px 20px; flex: 1; }
  .stat .num { font-size: 28px; font-weight: 700; color: #6c5ce7; }
  .stat .label { color: #888; font-size: 12px; margin-top: 4px; }
  .plan-list { display: flex; flex-direction: column; gap: 8px; }
  .plan-card { background: #1a1a2e; border: 1px solid #333; border-radius: 10px; padding: 16px 20px; display: flex; align-items: center; justify-content: space-between; transition: border-color 0.15s; }
  .plan-card:hover { border-color: #6c5ce7; }
  .plan-card.approved { border-color: #10b981; }
  .plan-info { flex: 1; }
  .plan-title { font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 4px; }
  .plan-meta { font-size: 12px; color: #666; }
  .plan-meta .approved-info { color: #10b981; margin-left: 8px; }
  .plan-actions { display: flex; gap: 8px; align-items: center; }
  .badge { font-size: 11px; padding: 3px 8px; border-radius: 20px; font-weight: 600; }
  .badge.public { background: #1b4332; color: #52b788; }
  .badge.private { background: #3d1f1f; color: #e07070; }
  .badge.approved { background: #064e3b; color: #10b981; }
  .badge.pending { background: #78350f; color: #fbbf24; }
  .btn { padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; border: 1px solid #444; text-decoration: none; }
  .btn-view { background: #6c5ce7; color: #fff; border-color: #6c5ce7; }
  .btn-view:hover { background: #5a4bd1; }
  .btn-approve { background: #10b981; color: #fff; border-color: #10b981; }
  .btn-approve:hover { background: #059669; }
  .btn-unapprove { background: transparent; color: #fbbf24; border-color: #fbbf24; }
  .btn-unapprove:hover { background: #78350f; }
  .btn-delete { background: transparent; color: #e07070; border-color: #5a3030; }
  .btn-delete:hover { background: #3d1f1f; }
  .empty { text-align: center; padding: 60px 20px; color: #666; }
  .empty p { margin-bottom: 16px; }
  .loading { text-align: center; padding: 40px; color: #666; }
  .error { background: #3d1f1f; border: 1px solid #5a3030; color: #e07070; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 13px; }
  .toast { position: fixed; bottom: 20px; right: 20px; background: #6c5ce7; color: #fff; padding: 10px 18px; border-radius: 8px; font-size: 13px; opacity: 0; transition: opacity 0.3s; pointer-events: none; }
  .toast.show { opacity: 1; }
  .preview-modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 100; }
  .preview-modal.open { display: flex; align-items: center; justify-content: center; }
  .preview-frame { width: 90vw; height: 85vh; background: #fff; border-radius: 12px; border: none; }
  .preview-close { position: fixed; top: 16px; right: 20px; background: #333; color: #fff; border: none; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 18px; z-index: 101; }
</style>
</head>
<body>

<div id="login-view" class="login-box" style="display:none;">
  <h2>Plan Dashboard</h2>
  <input type="email" id="email-input" placeholder="you@example.com" />
  <input type="password" id="password-input" placeholder="Password" />
  <button onclick="doLogin()">Login / Register</button>
  <p class="hint">Enter your email and password to login or create an account</p>
</div>

<div id="app-view" style="display:none;">
  <div class="header">
    <h1>Plan Dashboard</h1>
    <div style="display:flex;align-items:center;gap:12px;">
      <span class="email" id="user-email"></span>
      <button onclick="window.location.href='/dashboard'">Home</button>
      <button onclick="doLogout()">Logout</button>
    </div>
  </div>
  <div class="container">
    <div id="error-box" class="error" style="display:none;"></div>
    <div class="stats" id="stats"></div>
    <div id="plan-list" class="plan-list"></div>
  </div>
</div>

<div id="empty-view" class="empty" style="display:none;">
  <h2>No plans yet</h2>
  <p>Create your first plan with the CLI:</p>
  <code style="background:#1a1a2e;padding:8px 12px;border-radius:6px;display:inline-block;">plan create -p &lt;project-id&gt; -t "My Plan" --html plan.html</code>
</div>

<div class="preview-modal" id="preview-modal">
  <button class="preview-close" onclick="closePreview()">&times;</button>
  <iframe class="preview-frame" id="preview-frame"></iframe>
</div>

<div class="toast" id="toast"></div>

<script>
const API = window.location.origin;
let apiKey = localStorage.getItem('plan_api_key');
let userEmail = localStorage.getItem('plan_email');

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2000);
}

function show(id) {
  ['login-view','app-view','empty-view'].forEach(v => document.getElementById(v).style.display = 'none');
  document.getElementById(id).style.display = '';
}

function headers() {
  return { 'Authorization': 'Bearer ' + apiKey, 'Content-Type': 'application/json' };
}

async function doLogin() {
  const input = document.getElementById('email-input');
  const email = input.value.trim();
  const password = document.getElementById('password-input').value;
  if (!email || !email.includes('@')) {
    toast('Enter a valid email');
    return;
  }
  if (!password) {
    toast('Enter a password');
    return;
  }

  try {
    const res = await fetch(API + '/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email, password: password })
    });
    if (res.ok) {
      const data = await res.json();
      apiKey = data.api_key;
      userEmail = email;
      localStorage.setItem('plan_api_key', apiKey);
      localStorage.setItem('plan_email', email);
      loadPlans();
      return;
    }
  } catch (e) { }

  try {
    const res = await fetch(API + '/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email, password: password })
    });
    if (res.ok) {
      const data = await res.json();
      apiKey = data.api_key;
      userEmail = email;
      localStorage.setItem('plan_api_key', apiKey);
      localStorage.setItem('plan_email', email);
      toast('Account created!');
      loadPlans();
      return;
    }
    const err = await res.json().catch(() => ({}));
    toast(err.detail || 'Login failed');
  } catch (e) {
    toast('Connection error');
  }
}

function doLogout() {
  localStorage.removeItem('plan_api_key');
  localStorage.removeItem('plan_email');
  apiKey = null;
  userEmail = null;
  show('login-view');
}

function showError(msg) {
  const box = document.getElementById('error-box');
  box.textContent = msg;
  box.style.display = '';
}

async function loadPlans() {
  if (!apiKey) { show('login-view'); return; }
  show('app-view');
  document.getElementById('user-email').textContent = userEmail || '';
  document.getElementById('error-box').style.display = 'none';
  document.getElementById('plan-list').innerHTML = '<div class="loading">Loading plans...</div>';

  try {
    const res = await fetch(API + '/api/plans', { headers: headers() });
    if (!res.ok) {
      if (res.status === 401) {
        localStorage.removeItem('plan_api_key');
        apiKey = null;
        show('login-view');
        return;
      }
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to load plans');
    }
    const data = await res.json();
    const plans = data.plans || [];
    renderPlans(plans);
  } catch (e) {
    showError(e.message);
    document.getElementById('plan-list').innerHTML = '';
  }
}

function renderPlans(plans) {
  const list = document.getElementById('plan-list');
  const stats = document.getElementById('stats');

  const publicCount = plans.filter(p => p.is_public).length;
  const approvedCount = plans.filter(p => p.is_approved).length;
  const pendingCount = plans.filter(p => !p.is_approved).length;
  
  stats.innerHTML =
    '<div class="stat"><div class="num">' + plans.length + '</div><div class="label">Total Plans</div></div>' +
    '<div class="stat"><div class="num" style="color:#10b981">' + approvedCount + '</div><div class="label">Approved</div></div>' +
    '<div class="stat"><div class="num" style="color:#fbbf24">' + pendingCount + '</div><div class="label">Pending</div></div>' +
    '<div class="stat"><div class="num">' + publicCount + '</div><div class="label">Public</div></div>';

  if (plans.length === 0) {
    show('empty-view');
    return;
  }

  list.innerHTML = plans.map(p => {
    const date = p.updated_at ? new Date(p.updated_at).toLocaleDateString() : '';
    const publicBadge = p.is_public ? '<span class="badge public">Public</span>' : '<span class="badge private">Private</span>';
    const approvedBadge = p.is_approved ? '<span class="badge approved">Approved</span>' : '<span class="badge pending">Pending</span>';
    const approvedClass = p.is_approved ? ' approved' : '';
    const approvedInfo = p.is_approved && p.approved_by ? '<span class="approved-info">by ' + esc(p.approved_by) + '</span>' : '';
    
    const approveBtn = p.is_approved
      ? '<button class="btn btn-unapprove" onclick="unapprovePlan(\\'' + p.id + '\\')">Unapprove</button>'
      : '<button class="btn btn-approve" onclick="approvePlan(\\'' + p.id + '\\')">Approve</button>';
    
    return '<div class="plan-card' + approvedClass + '">' +
      '<div class="plan-info">' +
        '<div class="plan-title">' + esc(p.title) + '</div>' +
        '<div class="plan-meta">' + esc(p.id.slice(0,8)) + ' &middot; ' + date + approvedInfo + '</div>' +
      '</div>' +
      '<div class="plan-actions">' +
        publicBadge +
        approvedBadge +
        approveBtn +
        '<button class="btn btn-view" onclick="preview(\\'' + p.id + '\\', ' + p.is_public + ', \\'' + esc(p.slug) + '\\')">View</button>' +
        '<button class="btn btn-delete" onclick="delPlan(\\'' + p.id + '\\')">Delete</button>' +
      '</div>' +
    '</div>';
  }).join('');
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

async function preview(id, isPublic, slug) {
  if (isPublic) {
    window.open(API + '/p/' + slug, '_blank');
    return;
  }
  try {
    const res = await fetch(API + '/api/plans/' + id, { headers: headers() });
    if (!res.ok) throw new Error('Failed to load plan');
    const plan = await res.json();
    const modal = document.getElementById('preview-modal');
    const frame = document.getElementById('preview-frame');
    modal.classList.add('open');
    frame.srcdoc = plan.html_content;
  } catch (e) {
    toast('Error loading plan');
  }
}

function closePreview() {
  document.getElementById('preview-modal').classList.remove('open');
  document.getElementById('preview-frame').srcdoc = '';
}

async function approvePlan(id) {
  try {
    const res = await fetch(API + '/api/plans/' + id + '/approve', {
      method: 'POST',
      headers: headers()
    });
    if (res.ok) {
      toast('Plan approved!');
      loadPlans();
    } else {
      const err = await res.json().catch(() => ({}));
      toast(err.detail || 'Approve failed');
    }
  } catch (e) {
    toast('Approve failed');
  }
}

async function unapprovePlan(id) {
  try {
    const res = await fetch(API + '/api/plans/' + id + '/unapprove', {
      method: 'POST',
      headers: headers()
    });
    if (res.ok) {
      toast('Plan unapproved');
      loadPlans();
    } else {
      const err = await res.json().catch(() => ({}));
      toast(err.detail || 'Unapprove failed');
    }
  } catch (e) {
    toast('Unapprove failed');
  }
}

async function delPlan(id) {
  if (!confirm('Delete this plan?')) return;
  try {
    const res = await fetch(API + '/api/plans/' + id, { method: 'DELETE', headers: headers() });
    if (res.ok) {
      toast('Deleted');
      loadPlans();
    } else {
      toast('Delete failed');
    }
  } catch (e) {
    toast('Delete failed');
  }
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closePreview(); });
loadPlans();
</script>
</body>
</html>"""


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "service": "html-plan-service", "version": "0.1.0"}


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy"}


@app.get("/dashboard", response_class=HTMLResponse, tags=["dashboard"])
async def dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)


NAV_BAR = '''<div style="position:fixed;top:0;left:0;right:0;z-index:9999;display:flex;align-items:center;justify-content:space-between;padding:10px 20px;background:#1a1a2e;border-bottom:1px solid #333;">
  <a href="/dashboard" style="color:#6c5ce7;text-decoration:none;font-size:14px;font-weight:600;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">&larr; Dashboard</a>
</div>'''

BODY_PADDING = '<style>body{padding-top:48px!important}</style>'

@app.get("/p/{slug}", response_class=HTMLResponse, tags=["public"])
async def serve_public_plan(slug: str):
    plan = await Plan.filter(slug=slug, is_public=True).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    title = plan.title
    description = ""
    if plan.frontmatter:
        description = plan.frontmatter.get("description", "") or ""

    html = plan.html_content

    if "<head>" in html.lower():
        safe_title = title.replace('"', "&quot;")
        safe_desc = description.replace('"', "&quot;")
        meta_tags = f'''
    <meta property="og:title" content="{safe_title}">
    <meta property="og:description" content="{safe_desc}">
    <meta property="og:type" content="article">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{safe_title}">
    <meta name="twitter:description" content="{safe_desc}">
'''
        lower = html.lower()
        head_idx = lower.find("<head>")
        if head_idx != -1:
            insert_pos = head_idx + len("<head>")
            html = html[:insert_pos] + meta_tags + html[insert_pos:]

    lower = html.lower()
    body_idx = lower.find("<body>")
    if body_idx != -1:
        insert_pos = body_idx + len("<body>")
        html = html[:insert_pos] + NAV_BAR + BODY_PADDING + html[insert_pos:]
    else:
        html = NAV_BAR + html

    return HTMLResponse(content=html)


register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=False,
    add_exception_handlers=True,
)
