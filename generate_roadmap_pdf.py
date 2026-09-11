#!/usr/bin/env python3
"""PulseTrack AI - Complete Roadmap PDF generator (styled, professional)."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether, ListFlowable, ListItem, Image
)
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

OUT = r"C:\Users\vinayak\Downloads\fastapiProj\PulseTrack-AI-Roadmap.pdf"

# ---------- Colors ----------
INDIGO = HexColor("#4F46E5")
INDIGO_DARK = HexColor("#3730A3")
SLATE_DARK = HexColor("#0F172A")
SLATE = HexColor("#334155")
SLATE_LIGHT = HexColor("#64748B")
LIGHT_BG = HexColor("#F1F5F9")
LIGHT_BORDER = HexColor("#E2E8F0")
GREEN = HexColor("#16A34A")
GREEN_BG = HexColor("#DCFCE7")
AMBER = HexColor("#B45309")
AMBER_BG = HexColor("#FEF3C7")
BLUE_BG = HexColor("#DBEAFE")
BLUE_BORDER = HexColor("#93C5FD")
PURPLE_BG = HexColor("#EDE9FE")
SUCCESS_DARK = HexColor("#15803D")

W, H = A4

styles = getSampleStyleSheet()

sTitle = ParagraphStyle("Title2", parent=styles["Title"], fontSize=34, leading=38, textColor=HexColor("#FFFFFF"), alignment=TA_CENTER, fontName="Helvetica-Bold")
sSubtitle = ParagraphStyle("Subtitle2", parent=styles["Normal"], fontSize=13, leading=18, textColor=HexColor("#C7D2FE"), alignment=TA_CENTER, fontName="Helvetica")
sCoverMeta = ParagraphStyle("CoverMeta", parent=styles["Normal"], fontSize=9.5, leading=13, textColor=HexColor("#E0E7FF"), alignment=TA_CENTER, fontName="Helvetica")
sH1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=17, leading=22, textColor=HexColor("#FFFFFF"), backColor=INDIGO, borderPadding=(7,10,7), fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=10, alignment=TA_LEFT)
sH2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12.5, leading=16, textColor=INDIGO_DARK, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=6, borderPadding=(0,0,4))
sH3 = ParagraphStyle("H3", parent=styles["Heading3"], fontSize=10.5, leading=14, textColor=SLATE_DARK, fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4)
sBody = ParagraphStyle("Body2", parent=styles["Normal"], fontSize=9.5, leading=14.5, textColor=SLATE, fontName="Helvetica", alignment=TA_JUSTIFY, spaceAfter=5)
sBodySmall = ParagraphStyle("BodySmall", parent=sBody, fontSize=9, leading=13)
sBullet = ParagraphStyle("Bullet2", parent=sBody, leftIndent=16, firstLineIndent=0, spaceAfter=3, alignment=TA_LEFT)
sCode = ParagraphStyle("Code2", parent=styles["Code"], fontSize=7.8, leading=11, textColor=SLATE_DARK, fontName="Courier", alignment=TA_LEFT)
sTableCell = ParagraphStyle("TC", parent=styles["Normal"], fontSize=8.2, leading=11, textColor=SLATE, fontName="Helvetica", alignment=TA_LEFT)
sTableCellB = ParagraphStyle("TCB", parent=sTableCell, fontName="Helvetica-Bold", textColor=SLATE_DARK)
sTableHead = ParagraphStyle("TH", parent=styles["Normal"], fontSize=8.3, leading=11, textColor=HexColor("#FFFFFF"), fontName="Helvetica-Bold", alignment=TA_CENTER)
sCaption = ParagraphStyle("Cap", parent=styles["Normal"], fontSize=8, leading=11, textColor=SLATE_LIGHT, fontName="Helvetica-Oblique", alignment=TA_CENTER)
sFooter = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7.5, leading=10, textColor=HexColor("#94A3B8"), fontName="Helvetica", alignment=TA_CENTER)

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LIGHT_BORDER)
    canvas.setLineWidth(0.6)
    canvas.line(20*mm, 14*mm, W-20*mm, 14*mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(HexColor("#94A3B8"))
    canvas.drawCentredString(W/2, 10*mm, f"PulseTrack AI  •  Complete Build Roadmap  •  Page {doc.page}")
    canvas.restoreState()

def cover_footer(canvas, doc):
    pass

def section(num, title):
    return Paragraph(f"{num} &nbsp;&nbsp; {title}", sH1)

def h2(t):
    return Paragraph(t, sH2)

def h3(t):
    return Paragraph(t, sH3)

def p(t):
    return Paragraph(t, sBody)

def ps(t):
    return Paragraph(t, sBodySmall)

def bullets(items):
    story = []
    for it in items:
        story.append(Paragraph(f"<font color='#4F46E5'><b>▸</b></font> &nbsp;{it}", sBullet))
    return story

def numbered(items):
    story = []
    for i, it in enumerate(items, 1):
        story.append(Paragraph(f"<font color='#4F46E5'><b>{i}.</b></font> &nbsp;{it}", sBullet))
    return story

def callout(title, text, bg=BLUE_BG, border=BLUE_BORDER, title_color="#1E40AF"):
    inner = [
        [Paragraph(f"<b><font color='{title_color}'>{title}</font></b>", ParagraphStyle("co", parent=sBodySmall, textColor=HexColor(title_color), alignment=TA_LEFT)),
         Paragraph(text, ParagraphStyle("co2", parent=sBodySmall, alignment=TA_LEFT))]
    ]
    t = Table(inner, colWidths=[28*mm, 130*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), bg),
        ("BOX", (0,0), (-1,-1), 0.8, border),
        ("ROUNDEDCORNERS", [3,3,3,3]),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    return t

def code_block(lines):
    txt = "<br/>".join([l.replace(" ", "&nbsp;") for l in lines])
    inner = [[Paragraph(f"<font face='Courier'>{txt}</font>", sCode)]]
    t = Table(inner, colWidths=[158*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), HexColor("#F8FAFC")),
        ("BOX", (0,0), (-1,-1), 0.7, LIGHT_BORDER),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    return t

def styled_table(header, rows, widths, header_bg=INDIGO):
    data = [[Paragraph(h, sTableHead) for h in header]]
    for r in rows:
        data.append([Paragraph(c, sTableCell) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0,0), (-1,0), header_bg),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("GRID", (0,0), (-1,-1), 0.5, LIGHT_BORDER),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, HexColor("#F8FAFC")]),
    ]
    t.setStyle(TableStyle(style))
    return t

def hr():
    return HRFlowable(width="100%", thickness=0.7, color=LIGHT_BORDER, spaceBefore=6, spaceAfter=6)

def build():
    doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=16*mm, rightMargin=16*mm, topMargin=16*mm, bottomMargin=18*mm,
                            title="PulseTrack AI - Complete Build Roadmap", author="PulseTrack AI")
    story = []

    # ================= COVER =================
    # Dark cover block simulated with a big table
    cover_data = [
        [Paragraph("<font color='#A5B4FC' size=9><b>P Y T H O N &nbsp;•&nbsp; F A S T A P I &nbsp;•&nbsp; A I &nbsp;•&nbsp; D E V O P S</b></font>", sCoverMeta)],
        [Paragraph("PulseTrack AI", ParagraphStyle("ct", parent=sTitle, fontSize=42, leading=44))],
        [Paragraph("Uptime Monitoring + Status Page SaaS<br/>with AI Incident Analyst", ParagraphStyle("cs", parent=sSubtitle, fontSize=14, leading=19))],
        [Paragraph("Complete Step-by-Step Roadmap  •  Every Endpoint  •  Every Feature  •  From Zero to Deployment<br/>in Simple Words — 100% Free Stack — Intermediate Python Developer Level", sCoverMeta)],
    ]
    ct = Table(cover_data, colWidths=[178*mm])
    ct.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), SLATE_DARK),
        ("ROUNDEDCORNERS", [6,6,6,6]),
        ("LEFTPADDING", (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    # push cover down a bit
    story.append(Spacer(1, 10*mm))
    story.append(ct)
    story.append(Spacer(1, 6*mm))

    badges = styled_table(
        ["Backend", "Frontend", "Infra", "Cost"],
        [["FastAPI + Postgres<br/>+ Redis + Gemini", "React + TS + Vite<br/>+ Tailwind + Recharts", "Docker + GitHub Actions<br/>+ Render + Vercel", "<b>$0</b> — Neon + Upstash<br/>+ Resend + Supabase"]],
        [44*mm, 44*mm, 44*mm, 36*mm]
    )
    story.append(badges)
    story.append(Spacer(1, 5*mm))
    story.append(callout("READ THIS FIRST",
        "This is <b>not a todo app</b>. You build a real SaaS that pings websites every minute, creates incidents, sends alerts, shows a public status page, and uses Gemini AI to explain outages. Recruiters hire for this. Follow phases 0 to 10 in order. Do not skip testing, Docker and CI/CD — that is what makes you Intermediate.",
        bg=PURPLE_BG, border=HexColor("#C4B5FD"), title_color="#5B21B6"))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("Locked scope: 17 features  •  ~45 REST endpoints + 2 WebSockets  •  8 weeks  •  Target: 80%+ test coverage &nbsp;&nbsp;|&nbsp;&nbsp; Generated: Sept 2026 &nbsp;&nbsp;|&nbsp;&nbsp; Stack: Python 3.12, FastAPI, SQLAlchemy 2.0 Async, Alembic, uv, PostgreSQL 16, Redis 7, ARQ, React TS", sCaption))
    story.append(PageBreak())

    # ================= TOC =================
    story.append(section("•", "What Is Inside"))
    story.append(Spacer(1, 2*mm))
    toc_items = [
        "<b>1.</b> Project in Simple Words — story of 1 outage",
        "<b>2.</b> Final Locked Feature List — 17 features you will build",
        "<b>3.</b> Tech Stack — what + why + free limit",
        "<b>4.</b> How System Works — architecture + 3 flows in simple diagrams",
        "<b>5.</b> Database Design — 10 tables, what each stores",
        "<b>6.</b> Redis Design — 5 jobs Redis does",
        "<b>7.</b> Complete API Contract — every endpoint with simple meaning",
        "<b>8.</b> Workers & Scheduler — who pings, who alerts",
        "<b>9.</b> Frontend Pages — 7 screens",
        "<b>10.</b> Build Roadmap Phase 0–10 — exact tasks + done checklist",
        "<b>11.</b> Testing + Docker + CI/CD + Free Deployment Map",
        "<b>12.</b> Security, Caching, Rate-Limit Rules",
        "<b>13.</b> Gemini AI — prompts + money-saving rules",
        "<b>14.</b> 8-Week Timeline + Resume Lines + Interview Answers",
    ]
    story.extend(bullets(toc_items))
    story.append(Spacer(1, 3*mm))
    story.append(callout("HOW TO USE THIS DOC",
        "Read sections 1–4 today. Then build <b>one phase at a time</b>. Each phase has a <b>Done =</b> box. Do not start next phase until Done is true. This is how real teams work.",
        bg=GREEN_BG, border=HexColor("#86EFAC"), title_color="#166534"))

    # ================= 1 =================
    story.append(section("01", "Project in Simple Words"))
    story.append(h2("One-line idea"))
    story.append(p("PulseTrack AI is a website where you add your website link, we watch it day and night, and if it goes down we tell you fast and AI tells you why. Your customers see a public green/red status page."))
    story.append(h2("The 3 users"))
    story.extend(bullets([
        "<b>Owner / Admin</b> — creates team, adds members, sees billing limits, manages API keys and alerts.",
        "<b>Member / Agent</b> — adds monitors, acknowledges incidents, writes post-mortems.",
        "<b>Viewer / Customer (public)</b> — no login, only sees public status page <b>/s/my-shop</b>.",
        "One team = one company. Swiggy data never mixes with Zomato data. This is called <b>multi-tenancy</b>."
    ]))
    story.append(h2("Story of 1 outage — end to end"))
    story.extend(numbered([
        "<b>You add monitor:</b> URL = <b>https://my-shop.com</b>, check every <b>1 min</b>, alert if keyword <b>'Checkout'</b> missing, track SSL.",
        "<b>Worker pings every minute</b> and saves: <b>UP, 200, 180ms</b> in <b>checks</b> table. Dashboard dot stays green.",
        "<b>2 AM site dies</b> — 2 fails in a row → we create <b>Incident #45 OPEN</b>. No human needed.",
        "<b>Alert in 10 sec:</b> Email via Resend + Discord/Telegram webhook. If still down after 10 min → escalate to Admin.",
        "<b>AI explains:</b> reads last 20 checks + error. Writes: <i>'SSL expired 2h ago. Fix: renew cert, restart Nginx.'</i> Cached 24h.",
        "<b>You share status link</b> to customers. They see red + your update: <i>'We are fixing, back in 20 min.'</i>",
        "<b>Site recovers</b> → 2 UP in a row → incident auto-resolves, downtime = 34 min, uptime % recalculated, weekly AI report updated.",
    ]))
    story.append(callout("SIMPLE RULE",
        "API never pings websites. <b>Worker pings.</b> API only shows data. Redis is the postman between them. If Gemini is slow, API still stays fast because AI runs in background.",
        bg=AMBER_BG, border=HexColor("#FCD34A"), title_color="#92400E"))

    # ================= 2 =================
    story.append(section("02", "Final Locked Feature List — 17 Features"))
    story.append(p("We locked 8 core + 9 pro (added CSV export on request). Anything else goes to backlog. Do not add more during build."))
    story.append(h2("Core 8 — must have"))
    story.append(styled_table(
        ["#", "Feature", "What it does (simple)"],
        [
            ["C1", "Auth + Teams + Roles", "Register/login with JWT. Teams isolate data. Roles: owner / member / viewer."],
            ["C2", "Monitors CRUD", "Add / edit / pause / delete URL monitors with interval 1/5/10 min."],
            ["C3", "Periodic Checks", "Worker pings URL, saves UP/DOWN + latency + code + error every interval."],
            ["C4", "Incidents Auto", "2 fails → OPEN incident. 2 success → RESOLVED + downtime calc."],
            ["C5", "Alerts", "Email + Discord/Slack/Telegram webhook with retry 3x. Test button."],
            ["C6", "Dashboard + Charts", "Green/red dots, latency p50/p95 graph, uptime % 30d/90d, incident timeline."],
            ["C7", "Public Status Page", "Shareable /s/slug, no login, cached 30s, incident history."],
            ["C8", "API Docs + Health", "Auto Swagger docs, /health, /metrics, pagination + filters everywhere."],
        ], [10*mm, 42*mm, 106*mm]
    ))
    story.append(h2("Pro 9 — what makes you hired"))
    story.append(styled_table(
        ["#", "Feature", "What it does (simple) + why companies pay"],
        [
            ["P1", "Heartbeat (reverse monitor)", "Your cron pings us. If no ping in time → 'Cron dead' incident. For background jobs."],
            ["P2", "Keyword + API + SSL checks", "Check word exists, JSON field equals value, cert expiry days. Catches hacks."],
            ["P3", "Escalation + Maintenance", "Still down 10m → ping admin. Mute alerts during deploy window."],
            ["P4", "Badge + Subscribe", "Embed green badge in README. Visitors subscribe for UP emails."],
            ["P5", "API Keys + Outbound Webhooks", "Users automate via key. We POST signed JSON to their URL on incident."],
            ["P6", "Deploy Markers", "GitHub Action pings on deploy → vertical line on graph. Links outage to release."],
            ["P7", "AI Analyst + Post-mortem", "Explain outage + draft customer update + weekly report. Cached."],
            ["P8", "Audit Logs + Limits", "Who deleted what + when. Free plan = 10 monitors/team. Real SaaS logic."],
            ["P9", "CSV Export (NEW)", "One-click download: checks + incidents as CSV for Excel/Sheets. Boss-ready proof. $0, just code."],
        ], [10*mm, 42*mm, 106*mm], header_bg=HexColor("#0E7490")
    ))
    story.append(Spacer(1,2*mm))
    story.append(callout("BACKLOG — DO AFTER JOB",
        "Custom domains, SSO/OAuth Google, 2FA TOTP, multi-region checkers, SMS (Twilio paid), Stripe billing, mobile PWA push. Mention in README as <i>Future work</i> — shows vision without scope creep.",
        bg=LIGHT_BG, border=LIGHT_BORDER, title_color="#334155"))

    # ================= 3 =================
    story.append(section("03", "Tech Stack — Free Forever"))
    story.append(styled_table(
        ["Layer", "Choice", "Why + Free limit (simple)"],
        [
            ["Language", "Python 3.12", "Modern, async, type hints. Required for job."],
            ["API", "FastAPI + Pydantic v2", "Fast, auto Swagger docs, async. Best Python API framework now."],
            ["ORM + Migration", "SQLAlchemy 2.0 Async<br/>+ Alembic", "Industry standard. Async = handles many checks at once."],
            ["Env", "uv", "Superfast venv + packages. Replaces pip + venv."],
            ["DB prod", "Neon Postgres 16", "Free 512 MB + pgvector for AI search. Enough for portfolio."],
            ["DB local", "Docker Postgres 16", "Same as prod, runs offline."],
            ["Cache/Queue", "Upstash Redis (prod)<br/>Docker Redis 7 (local)", "Free 10k cmds/day. Queue + cache + live updates + locks."],
            ["Worker", "ARQ", "Async Redis queue, made for FastAPI. Lighter than Celery."],
            ["Frontend", "React + TS + Vite<br/>+ Tailwind + shadcn/ui<br/>+ TanStack Query + Recharts", "Most in-demand. Decoupled SPA proves JWT + REST skills. Free on Vercel. Charts perfect for latency."],
            ["AI", "Gemini 2.0 Flash Free", "Free tier ~15 req/min. Only on-demand + cached. Never in hot loop."],
            ["Email", "Resend Free", "100 emails/day free. Enough for demo alerts."],
            ["Alerts extra", "Discord / Slack webhook<br/>+ Telegram Bot", "100% free, unlimited. No SMS cost."],
            ["Files", "None needed", "No uploads in v1 — keeps it free + simple."],
            ["Infra", "Docker + Compose<br/>GitHub Actions<br/>Render Free + Vercel Free", "Render sleeps on free — mention cold start. Docker proves DevOps."],
        ], [28*mm, 48*mm, 82*mm]
    ))
    story.append(Spacer(1,2*mm))
    story.append(p("Folder structure you will use from Day 1 (this is what seniors expect):"))
    story.append(code_block([
        "backend/app/{main.py, core/{config.py,security.py,logging.py,rate_limit.py},",
        "&nbsp;&nbsp;api/v1/routers/{auth,teams,monitors,checks,incidents,ai,heartbeats,",
        "&nbsp;&nbsp;&nbsp;&nbsp;maintenance,notifications,api_keys,webhooks,status,deploys,audit}.py,",
        "&nbsp;&nbsp;models/, schemas/, services/, repositories/, workers/{scheduler,checker,alerter}.py}",
        "frontend/src/{pages/{Login,Dashboard,MonitorDetail,Incidents,StatusPage},",
        "&nbsp;&nbsp;components/ui, hooks, lib/api-client.ts}",
        "docker-compose.yml, Dockerfile, .github/workflows/ci.yml",
    ]))

    # ================= 4 =================
    story.append(section("04", "How System Works — 3 Flows"))
    story.append(h2("A. Big picture"))
    story.append(code_block([
        "[React on Vercel] --REST+WS--> [FastAPI on Render] --SQL--> [Neon Postgres]",
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|--> [Upstash Redis: queue/cache/pubsub/lock]",
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ARQ Worker] --ping--> [User Websites]",
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ARQ Worker] --alert--> [Email/Discord/Telegram]",
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[FastAPI/Worker] --prompt--> [Gemini Free]",
    ]))
    story.append(h2("B. Monitoring loop (every minute)"))
    story.extend(numbered([
        "Scheduler every 30s: find monitors where <b>next_check_at <= now</b> → push job <b>check(monitor_id)</b> to Redis.",
        "Worker pops job, takes Redis lock <b>lock:monitor:{id}</b> (so 2 workers don't double-check).",
        "Worker does <b>httpx GET timeout=10s</b>, measures latency, reads code + body + SSL days.",
        "Decide UP/DOWN: DOWN if timeout / code >=500 / keyword missing / SSL <7 days (warning). Save to <b>checks</b>.",
        "Set <b>next_check_at = now + interval</b>. Update cache <b>status:{id}</b>. Publish WS event.",
        "Flap logic: look at last 2 checks. <b>DOWN+DOWN + no open incident → create incident + alert.</b> UP+UP + open incident → resolve.",
    ]))
    story.append(h2("C. Alert + AI flow (cheap)"))
    story.extend(bullets([
        "Alert sender reads <b>notification_channels</b> for team → sends Email + Webhooks in parallel → retry 3x with backoff → log to <b>alert_logs</b>.",
        "If still DOWN after 10 min and not acked → escalate to owner channel. If in <b>maintenance window</b> → skip alert, only log.",
        "AI only on button click: fetch last 20 checks + incident → check Redis <b>ai:{incident_id}</b> → if hit return in 50ms ($0). Else 1 Gemini call → save to <b>incidents.ai_summary</b> + Redis 24h.",
    ]))
    story.append(callout("INTERVIEW LINE",
        "\"I keep pings out of request path. API returns fast. Workers scale separately. AI is cached so free quota never burns. Public status page is cached 30s so viral traffic can't kill DB.\"",
        bg=GREEN_BG, border=HexColor("#86EFAC"), title_color="#166534"))

    # ================= 5 =================
    story.append(section("05", "Database Design — 10 Tables"))
    story.append(p("Postgres stores truth. Redis stores speed. Never swap. All tables have <b>team_id</b> so teams can't see each other. Add index on <b>(team_id, ...)</b> everywhere."))
    story.append(styled_table(
        ["Table", "Key columns (simple meaning)", "Relation"],
        [
            ["teams", "id, name, slug (for status URL), plan (free/pro)", "1 team → many users, monitors"],
            ["users", "id, team_id, email, password_hash, role, is_active", "belongs to team"],
            ["monitors", "id, team_id, name, url, method, interval_min, keyword, json_path, ssl_check, is_paused, next_check_at", "1 monitor → many checks, incidents"],
            ["checks", "id, monitor_id, status UP/DOWN, latency_ms, code, error, checked_at", "append-only, partitioned by month, BRIN index"],
            ["incidents", "id, monitor_id, team_id, status OPEN/ACK/RESOLVED, started_at, ack_at, resolved_at, downtime_sec, ai_summary", "1 incident → many comments, alerts"],
            ["incident_comments", "id, incident_id, user_id, body, created_at", "timeline chat"],
            ["heartbeats", "id, team_id, name, ping_key, period_min, grace_min, last_ping_at, status", "reverse monitor"],
            ["maintenance_windows", "id, team_id, monitor_id (null=all), starts_at, ends_at, reason", "mute alerts in window"],
            ["notification_channels", "id, team_id, type email/discord/slack/telegram, config JSON, is_active", "where to shout"],
            ["api_keys + webhooks<br/>+ audit_logs + deploys", "api_keys: prefix, hash. outbound_webhooks: url, secret. audit: who did what. deploys: version, marked_at", "platform + trust"],
        ], [32*mm, 78*mm, 48*mm]
    ))
    story.append(Spacer(1,2*mm))
    story.append(p("<b>Checks table will be biggest.</b> 10 monitors × every 1 min = 14,400 rows/day. That's fine. Use <b>BRIN index on checked_at</b>, keep only 90 days (cron deletes old), and never JOIN full table — always filter by monitor_id + time range. Mention this in interview."))
    story.append(code_block([
        "teams (1) --- (*) users &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; monitors (1) --- (*) checks (append-only)",
        "teams (1) --- (*) monitors --- (*) incidents --- (*) incident_comments",
        "teams (1) --- (*) heartbeats | maintenance | channels | api_keys | audit_logs",
    ]))

    # ================= 6 =================
    story.append(section("06", "Redis Design — 5 Jobs"))
    story.append(styled_table(
        ["Use", "Key example", "Simple rule"],
        [
            ["1. Queue", "arq:queue → check(12)", "Scheduler pushes, worker pops. Retry 3x."],
            ["2. Cache", "status:{monitor_id} TTL 60s<br/>public:{slug} TTL 30s, ai:{incident} TTL 24h", "Read cache first. Delete on write (invalidate)."],
            ["3. Lock", "lock:monitor:{id} TTL 30s", "Only 1 worker checks same monitor. Prevents double alerts."],
            ["4. Pub/Sub", "channel:live → {monitor_id, status}", "Worker publishes, API forwards to WebSocket. Live dot without refresh."],
            ["5. Rate-limit + blacklist", "rl:{ip}:{min}, jwt:black:{jti}", "AI 10/min, pings 60/min. Logout token blocked till expiry."],
        ], [30*mm, 55*mm, 73*mm]
    ))

    # ================= 7 =================
    story.append(section("07", "Complete API Contract — Every Endpoint"))
    story.append(p("Base URL local: <b>http://localhost:8000/api/v1</b>. Auth: <b>Bearer JWT</b> except public status + heartbeat ping (uses key). All lists support <b>?page&limit&search&status&sort</b>. All mutating routes write audit log."))
    story.append(callout("HOW TO READ TABLE",
        "Method + Path → what it does in simple words. Build in this order. Starred (*) = demo wow.",
        bg=LIGHT_BG, border=LIGHT_BORDER, title_color="#334155"))

    def ep_table(title, rows):
        s = []
        s.append(h3(title))
        s.append(styled_table(["Method + Path", "Auth", "What it does (simple)"], rows, [62*mm, 22*mm, 74*mm], header_bg=HexColor("#1E3A8A")))
        s.append(Spacer(1,2*mm))
        return s

    story.extend(ep_table("Auth (5)", [
        ["<b>POST /auth/register</b><br/>{name,email,password,team_name}", "No", "Create team + owner user. Hash password bcrypt."],
        ["<b>POST /auth/login</b><br/>{email,password}", "No", "Check password → return access 15m + refresh 7d."],
        ["<b>POST /auth/refresh</b><br/>{refresh_token}", "No", "Rotate refresh, block reuse (reuse = theft)."],
        ["<b>POST /auth/logout</b>", "JWT", "Blacklist access jti in Redis till expiry."],
        ["<b>GET /auth/me</b>", "JWT", "Return my profile + team + role."],
    ]))
    story.extend(ep_table("Teams + Members (4)", [
        ["<b>GET /teams/me</b>", "JWT", "My team info + plan + monitor count/limit."],
        ["<b>PUT /teams/me</b> {name}", "Owner", "Rename team / change status slug."],
        ["<b>GET /teams/members</b>", "JWT", "List members with roles."],
        ["<b>POST /teams/invite</b> {email,role}", "Owner", "Invite member (v1: direct add, v2: email link)."],
    ]))
    story.extend(ep_table("Monitors (7) — core", [
        ["<b>POST /monitors</b><br/>{name,url,interval,keyword}", "Member+", "Validate URL, enforce free limit 10, set next_check_at=now."],
        ["<b>GET /monitors</b> ?status", "JWT", "List with live cached status + last latency. Cached 60s."],
        ["<b>GET /monitors/{id}</b>", "JWT", "Detail + uptime % + last 20 checks. Check team owns it."],
        ["<b>PUT /monitors/{id}</b>", "Member+", "Edit URL/interval/keyword. Invalidate cache. Audit."],
        ["<b>DELETE /monitors/{id}</b>", "Owner", "Delete + cascade checks/incidents. Audit."],
        ["<b>POST /monitors/{id}/pause</b>", "Member+", "Skip scheduler until resume."],
        ["<b>POST /monitors/{id}/resume</b>", "Member+", "Set next_check_at=now."],
    ]))
    story.extend(ep_table("Checks + Stats + Export (4)", [
        ["<b>GET /monitors/{id}/checks</b><br/>?from&to&limit", "JWT", "Time-series rows for graph. Never full scan — paginated."],
        ["<b>GET /monitors/{id}/stats</b> ?days=30", "JWT", "Uptime %, avg/p95 latency, incidents count, MTTR. Computed from checks."],
        ["<b>GET /monitors/{id}/checks/export</b><br/>?from&to (CSV)", "JWT", "Download checks as CSV: checked_at,status,latency_ms,code,error. Streaming, max 50k rows."],
        ["<b>GET /incidents/export</b> ?status (CSV)", "JWT", "Download incidents as CSV: id,monitor,started,resolved,downtime_min,ai_summary. For boss/Excel."],
    ]))
    story.extend(ep_table("Incidents (7)", [
        ["<b>GET /incidents</b> ?status", "JWT", "All incidents newest first, with monitor name."],
        ["<b>GET /incidents/{id}</b>", "JWT", "Detail + timeline + AI summary if exists."],
        ["<b>POST /incidents/{id}/acknowledge</b>", "Member+", "I am looking. Stops escalation timer."],
        ["<b>POST /incidents/{id}/resolve</b> {note}", "Member+", "Manual resolve + downtime calc."],
        ["<b>GET /monitors/{id}/incidents</b>", "JWT", "History per monitor for status page."],
        ["<b>POST /incidents/{id}/comments</b> {body}", "Member+", "Add timeline note. WS broadcast."],
        ["<b>GET /incidents/{id}/timeline</b>", "JWT", "Unified feed: created → alerts → acks → comments → resolved."],
    ]))
    story.extend(ep_table("AI (4) *", [
        ["<b>POST /incidents/{id}/analyze</b>", "Member+", "Gemini explains cause + fix. Cached 24h. Rate-limit 10/min."],
        ["<b>GET /incidents/{id}/analysis</b>", "JWT", "Return cached AI summary (50ms, $0)."],
        ["<b>POST /incidents/{id}/draft-update</b><br/>{tone:friendly}", "Member+", "Draft customer status message to copy-paste."],
        ["<b>POST /ai/ask</b> {question}", "Member+", "Ask 'why down Tuesday?' — searches past incidents. 1 call."],
    ]))
    story.extend(ep_table("Heartbeats (4)", [
        ["<b>POST /heartbeats</b> {name,period}", "Member+", "Create reverse monitor, returns secret ping_key."],
        ["<b>GET /heartbeats</b>", "JWT", "List with status ALIVE/MISSING."],
        ["<b>POST /heartbeats/{key}/ping</b>", "Key (no JWT)", "Cron calls this. Updates last_ping_at. Public but unguessable."],
        ["<b>DELETE /heartbeats/{id}</b>", "Member+", "Delete heartbeat."],
    ]))
    story.extend(ep_table("Maintenance + Channels + Keys + Webhooks (10)", [
        ["<b>POST /maintenance</b> {monitor_id?,starts,ends}", "Member+", "Mute window. Scheduler checks before alert."],
        ["<b>GET /maintenance</b> / <b>DELETE /maintenance/{id}</b>", "JWT", "List / cancel window."],
        ["<b>POST /notification-channels</b><br/>{type,config}", "Member+", "Add Email/Discord/Telegram. Encrypt secret."],
        ["<b>GET /notification-channels</b>", "JWT", "List channels + last delivery status."],
        ["<b>POST /notification-channels/{id}/test</b>", "Member+", "Send 'Test OK' to verify. Shows errors clearly."],
        ["<b>POST /api-keys</b> {name}", "Owner", "Create pk_live_... Return once. Store hash only."],
        ["<b>GET /api-keys</b> / <b>DELETE /api-keys/{id}</b>", "Owner", "List prefix + revoke."],
        ["<b>POST /webhooks/outbound</b> {url,secret}", "Member+", "We POST signed JSON on incident. HMAC header."],
        ["<b>POST /webhooks/outbound/{id}/test</b>", "Member+", "Send sample payload."],
        ["<b>GET /audit-logs</b> ?user&action", "Owner", "Who did what, when. Immutable."],
    ]))
    story.extend(ep_table("Public Status Page (4, no auth) *", [
        ["<b>GET /status/{slug}</b>", "Public", "Team name + monitors live status. Cached 30s."],
        ["<b>GET /status/{slug}/incidents</b>", "Public", "Last 90d incidents for history bars."],
        ["<b>POST /status/{slug}/subscribe</b> {email}", "Public RL", "Subscribe for UP emails. Rate-limit strict."],
        ["<b>GET /status/{slug}/badge.svg</b>", "Public", "Green/red SVG for README. Cache 60s."],
    ]))
    story.extend(ep_table("Deploys + System (4)", [
        ["<b>POST /monitors/{id}/deploys</b><br/>{version} + API-Key", "API-Key", "Mark deploy → vertical line on graph. From GitHub Action."],
        ["<b>GET /monitors/{id}/deploys</b>", "JWT", "List markers to overlay on chart."],
        ["<b>GET /health</b>", "Public", "200 {status:ok, db:up, redis:up}. Used by Render + CI."],
        ["<b>WS /ws/monitors</b> + <b>/ws/incidents/{id}</b>", "JWT", "Live push: status change, new comment. Via Redis pub/sub."],
    ]))
    story.append(callout("REQUEST / RESPONSE SHAPE (follow everywhere)",
        "Send JSON with Pydantic validation. Return <b>{data, meta:{page,total}, error:null}</b> or <b>{error:{code,message}}</b>. Errors: 400 bad input, 401 no login, 403 wrong role, 404 not found or not your team, 429 too many, 502 target site failed (not your bug).",
        bg=AMBER_BG, border=HexColor("#FCD34A"), title_color="#92400E"))

    # ================= 8 =================
    story.append(section("08", "Workers & Scheduler — Who Does What"))
    story.extend(bullets([
        "<b>Scheduler (every 30s, ARQ cron):</b> SELECT monitors WHERE next_check_at &lt;= now AND not paused → enqueue <b>check_job</b>. Also enqueue <b>heartbeat_checker</b> (missing pings) + <b>ssl_checker</b> (daily) + <b>cleanup_old_checks</b> (daily, keep 90d).",
        "<b>check_job(monitor_id):</b> lock → httpx GET (10s timeout, follow redirects, UA PulseTrack) → measure ms → keyword/JSON/SSL asserts → save check → update next_check_at → cache+pub → incident logic → unlock. Timeout or exception = DOWN, never crash worker.",
        "<b>alert_job(incident_id):</b> load channels → send parallel (asyncio.gather) → Resend email + webhook POSTs → save alert_logs with success/error → schedule escalation check in 10m if still OPEN and not acked.",
        "<b>ai_job(incident_id, type):</b> build tiny prompt (last 20 checks only, ~800 tokens) → Gemini Flash → save + cache. If quota 429 → save 'AI busy, retry' and backoff, don't fail incident.",
        "<b>Scale story:</b> run 1 API + 2 workers locally via Compose. In interview: 'Workers scale horizontally because Redis lock prevents double work.'",
    ]))
    story.append(code_block([
        "ARQ jobs: check_job | heartbeat_job | alert_job | escalate_job | ai_job | cleanup_job",
        "Retries: check x0 (next tick will retry), alert x3 backoff 30s/2m/10m, webhook x3",
        "Timeouts: HTTP 10s, Gemini 20s, email 10s, total job < 45s",
    ]))

    # ================= 9 =================
    story.append(section("09", "Frontend — 7 Screens + Export"))
    story.append(styled_table(
        ["Screen", "What user sees + does", "Key lib"],
        [
            ["Login / Register", "Simple centered card, JWT stored httpOnly? v1: memory+localStorage, auto-refresh.", "React Router, Zustand"],
            ["Dashboard", "Cards: Uptime now, Open incidents, p95 latency. Table of monitors with green/red dot auto-refresh 30s.", "TanStack Query, Recharts"],
            ["Monitor Detail", "Big latency area chart + deploy markers + checks table + incidents list + Pause/Resume + Export CSV button.", "Recharts, date-fns"],
            ["Incidents", "Filter OPEN/RESOLVED, click → timeline + Acknowledge/Resolve + AI Explain + Draft update + Export CSV.", "Query + WS"],
            ["Heartbeats + Maintenance", "Cron ping URL with copy button + last ping ago. Calendar-ish mute list.", "shadcn/ui"],
            ["Settings: Channels, Keys, Webhooks", "Add Discord URL → Test button shows green tick. Create API key → show once modal.", "Forms + Zod"],
            ["Public Status /s/slug *", "No login. Big green/red banner, 90-day bars, subscribe input, badge copy snippet.", "Vercel ISR, cached"],
        ], [34*mm, 88*mm, 36*mm]
    ))
    story.append(p("CSV Export buttons: Monitor Detail → 'Export checks CSV' downloads checked_at,status,latency_ms,code,error. Incidents page → 'Export incidents CSV'. Uses StreamingResponse text/csv, filename pulsetrack-checks-{id}.csv. Design rule: dark slate header, white cards, green #16A34A for UP, red #DC2626 for DOWN, amber for ACK."))

    # ================= 10 =================
    story.append(section("10", "Build Roadmap Phase 0–10"))
    story.append(callout("GOLDEN RULE",
        "One phase = one PR merged to main. Each phase ends with tests passing + Docker up. Never start next phase on broken main.",
        bg=GREEN_BG, border=HexColor("#86EFAC"), title_color="#166534"))

    phases = [
        ("PHASE 0 — Setup (Day 1–2)", "Init + Docker hello",
         ["uv init pulsetrack-ai, uv venv, add fastapi uvicorn sqlalchemy alembic pydantic-settings httpx arq redis pytest.",
          "Init git, GitHub repo, .gitignore, .env.example (DATABASE_URL, REDIS_URL, JWT_SECRET, GEMINI_KEY).",
          "Write docker-compose.yml: api (hot reload), db postgres:16, redis:7. Verify GET /health returns ok."],
         "Done = docker compose up works, /health 200, /docs opens."),
        ("PHASE 1 — Auth + Teams + RBAC (Week 1)", "Login that is safe",
         ["Models: teams, users. Alembic migration 001. Seed 1 team + owner.",
          "POST register/login/refresh/logout + GET me. Bcrypt hash, JWT 15m/7d, Redis blacklist.",
          "Dependency require_role. Write 8 pytest: login ok, wrong pass 401, viewer cannot delete (403), refresh reuse blocked."],
         "Done = 8 auth tests green, Swagger login works, audit logs auth events."),
        ("PHASE 2 — Monitors + Checks Read (Week 2)", "CRUD before magic",
         ["Models monitors + checks. Migration 002 with indexes (team_id, next_check_at, BRIN checked_at).",
          "Build 7 monitor endpoints + 2 checks/stats (mock data first). Enforce 10/team limit + URL validator + audit.",
          "Frontend: dashboard table + add-monitor form. TanStack Query caching."],
         "Done = create 10 monitors, pause/resume works, stats returns correct % on fake data."),
        ("PHASE 3 — Real Worker + Scheduler (Week 3) ★ HARDEST", "The heart",
         ["ARQ setup: scheduler cron 30s + check_job with httpx 10s timeout, UA header, redirect follow.",
          "Implement keyword + JSON-path + SSL-days asserts. Lock per monitor. Update next_check_at.",
          "Flap logic: 2x DOWN→OPEN, 2x UP→RESOLVE + downtime_sec. Test with httpbin.org + bad URL."],
         "Done = add https://example.com 1min, see live checks rows growing, kill URL → incident OPEN in ~2 min."),
        ("PHASE 4 — Alerts + Escalation + Maintenance (Week 3–4)", "Shout correctly",
         ["Models channels + alert_logs + maintenance. Resend + generic webhook sender with httpx + retry.",
          "Alert on OPEN, resolve mail on RESOLVE. Escalate if OPEN 10m unacked. Skip if in maintenance.",
          "Channels UI + Test button. Subscribe to Discord webhook yourself to see real alert."],
         "Done = downtime triggers real Discord msg + email, maintenance mutes correctly."),
        ("PHASE 5 — Live + Public Page + Heartbeat (Week 4)", "Wow demo",
         ["Redis pub/sub → WS /ws/monitors. React dot updates without refresh.",
          "Public /status/{slug} cached 30s + badge.svg + subscribe. Heartbeat create/ping/missing logic.",
          "Deploy markers POST + overlay on chart."],
         "Done = share status link in incognito (no login) works, badge green, cron ping demo works."),
        ("PHASE 6 — Gemini AI (Week 5) ★ DIFFERENTIATOR", "Smart but cheap",
         ["Prompt v1 analyze: 'You are SRE. Given 20 checks JSON, give: likely cause (1 line), evidence (2 bullets), fix (3 steps). Max 150 words.'",
          "draft-update prompt with tone param. ask endpoint with pgvector? v1: keyword search past incidents.",
          "Cache ai:{id} 24h + rate-limit 10/min. Handle 429 gracefully. UI: Explain button + copy draft."],
         "Done = click Explain → cached in 50ms second time, 1 Gemini call logged, quota safe."),
        ("PHASE 7 — Keys + Webhooks + Audit (Week 5–6)", "Platform trust",
         ["API keys: generate pk_live_ + hash sha256, middleware accepts Bearer pk_ OR JWT. Scope team.",
          "Outbound webhooks with HMAC X-Signature + test payload. Audit log on every write (user, action, target).",
          "Docs page with curl examples for keys + webhooks."],
         "Done = curl with API key creates monitor, webhook.site receives signed incident JSON."),
        ("PHASE 8 — Testing + Polish + CSV Export (Week 6)", "Prove quality",
         ["pytest 40+ tests: flap, escalation skip in maintenance, RBAC, cache hit, AI mocked, WS connect + CSV export content-type + team isolation. Coverage 80%+.",
          "Build CSV export: StreamingResponse text/csv with csv module, filter by team_id, limit 50k, filename header. Buttons in React download via blob URL.",
          "Ruff + Mypy + pre-commit. Seed demo data script (team Demo, 5 monitors, 1 open incident). Empty states, toasts, skeletons, mobile responsive."],
         "Done = pytest -q green, /checks/export returns valid CSV, coverage badge, demo login works for recruiter in 30s."),
        ("PHASE 9 — Docker + CI/CD (Week 7)", "Ship like pro",
         ["Multi-stage Dockerfile (slim, non-root, healthcheck). docker-compose.prod.yml.",
          "GitHub Actions: lint → mypy → pytest → docker build. Branch protection on main.",
          "Render Blueprint + Neon + Upstash env vars. Alembic migrate on deploy. Vercel env VITE_API_URL."],
         "Done = git push → Actions green → Render auto-deploys → /health ok prod."),
        ("PHASE 10 — Launch + Portfolio (Week 7–8)", "Get job",
         ["README: live demo links (dashboard + status page), arch diagram, API table, test badge, $0 cost table, demo creds.",
          "Loom 3-min video: add monitor → kill it → alert → AI explain → resolve. Add to LinkedIn + resume.",
          "Load test: 20 monitors 1min for 1h, screenshot p95 graph. Write post-mortem of your own outage."],
         "Done = recruiter can click 2 links and understand in 60s without calling you."),
    ]
    for title, sub, tasks, done in phases:
        story.append(h2(title))
        story.append(Paragraph(f"<i>{sub}</i>", ParagraphStyle("sub2", parent=sBodySmall, textColor=SLATE_LIGHT)))
        story.extend(bullets(tasks))
        story.append(Spacer(1,1*mm))
        story.append(callout("Done =", done, bg=GREEN_BG, border=HexColor("#86EFAC"), title_color="#166534"))
        story.append(Spacer(1,1*mm))

    # ================= 11 =================
    story.append(section("11", "Testing + Docker + CI/CD + Free Deploy"))
    story.append(h2("Testing — what to test"))
    story.extend(bullets([
        "<b>Unit:</b> decide_up_down(), stats calc, HMAC sign, prompt builder (no network).",
        "<b>API:</b> auth, RBAC deny, monitor limit 11th fails 403, public page no auth ok, private without token 401.",
        "<b>Worker:</b> mock httpx transport — DOWN+DOWN creates 1 incident (not 2), maintenance skips alert, resolve computes downtime.",
        "<b>Run:</b> <b>pytest -q --cov=app --cov-fail-under=80</b>. Mock Gemini + Resend, never hit real in tests.",
    ]))
    story.append(h2("Docker — simple"))
    story.append(code_block([
        "Dockerfile: python:3.12-slim → uv sync → non-root appuser → CMD uvicorn + alembic upgrade",
        "Compose local: api:8000 + db:5432 + redis:6379 + worker (same image, CMD arq)",
        "Compose prod: same image, env from Render/Neon/Upstash, no volumes",
    ]))
    story.append(h2("CI/CD pipeline"))
    story.append(code_block([
        "git push → GitHub Actions: ruff → mypy → pytest (postgres+redis services) → docker build test",
        "main merge → deploy backend → Render (auto) → run migrations → deploy frontend → Vercel",
        "PR must be green to merge. Add badges: build | coverage | python 3.12 | docker",
    ]))
    story.append(h2("Free deploy map — copy this"))
    story.append(styled_table(
        ["What", "Where Free", "Env var / note"],
        [
            ["Backend API + Worker (1 service)", "Render Free (750h/mo)", "1 instance only. No SSH/disk. See FREE CATCH below."],
            ["Postgres", "Neon Free 512MB (use this, NOT Render Postgres)", "DATABASE_URL pooled. Enable pgvector. Render Free DB expires in 30 days."],
            ["Redis", "Upstash Free 10k/day (use this, NOT Render Key Value)", "REDIS_URL. 10 monitors x 1min = ~3k cmds/day — safe. Render Free KV loses data on restart."],
            ["Frontend", "Vercel Free", "VITE_API_URL=https://your-api.onrender.com"],
            ["Email", "Resend Free 100/day", "From onboarding@resend.dev for demo."],
            ["Alerts", "Discord/Slack/Telegram", "Unlimited free. Use for demo video."],
        ], [42*mm, 42*mm, 74*mm]
    ))
    story.append(Spacer(1,3*mm))
    story.append(callout("FREE CATCH — RENDER SLEEPS AFTER 15 MIN (LOCKED DECISION: STAY ON FREE)",
        "Render Free web service <b>spins down after 15 min with no traffic</b>. You do <b>NOT restart manually</b> — it auto-wakes on next request in ~50 sec. <b>Catch for this project:</b> when asleep, your 1-min checks + worker also stop, so graphs will show gaps. <b>Free fix we will use:</b> ping <b>GET /health</b> every 14 min via <b>cron-job.org (free) or UptimeRobot (free)</b> to keep it awake. 1 always-awake service = ~720h/mo, fits in 750h free quota. Mention cold-start + keep-alive in README so recruiters know you understand free-tier trade-offs. Render Free Postgres/Key Value NOT used — Neon + Upstash stay always-on free.",
        bg=AMBER_BG, border=HexColor("#FCD34A"), title_color="#92400E"))
    story.append(Spacer(1,2*mm))
    story.append(code_block([
        "Keep-alive (free): cron-job.org → GET https://your-api.onrender.com/health every 14 min",
        "Render start CMD (free, 1 service runs both): web: alembic upgrade head && uvicorn app.main:app",
        "&nbsp;&nbsp;+ arq worker in same service via start.sh (Render Free has no separate Background Worker)",
        "Result: $0/mo, always-awake within 750h, checks keep running. Upgrade to $7/mo Starter only if you want no sleep.",
    ]))

    # ================= 12 =================
    story.append(section("12", "Security, Cache, Rate-Limit — Rules to Memorize"))
    story.append(styled_table(
        ["Area", "Rule (simple)"],
        [
            ["Auth", "Bcrypt cost 12, JWT secret 32+ chars, access 15m, refresh rotate + reuse detection."],
            ["Tenancy", "Every query filters team_id. Middleware loads team from JWT/API-key. Test cross-team 404."],
            ["Keys", "Show key once, store SHA256 hash + prefix for lookup. Revoke = delete."],
            ["Webhooks", "Sign body HMAC-SHA256 with secret, header X-Signature + timestamp, verify 5m skew."],
            ["Cache", "Status 60s, public 30s, badge 60s, AI 24h. Invalidate on write. Never cache auth/me."],
            ["Rate-limit", "Login 5/min/IP, AI 10/min/user, public subscribe 5/min/IP, ping 60/min/key. Return 429 + Retry-After."],
            ["Validation", "Pydantic URL HttpUrl, interval in [1,5,10,30], keyword max 200 chars. SQLAlchemy bound params only."],
        ], [30*mm, 128*mm]
    ))

    # ================= 13 =================
    story.append(section("13", "Gemini AI — Prompts + Saving Money"))
    story.append(p("Model: <b>gemini-2.0-flash</b>. Temperature 0.2 (factual). Max tokens 400. Timeout 20s. Always send <b>only last 20 checks</b>, never full history. Log tokens per call."))
    story.append(h3("Prompt 1 — analyze (copy-paste ready)"))
    story.append(code_block([
        "You are a senior SRE. Given monitor {url} and 20 checks JSON [{at,code,latency,error}],",
        "return: 1) Likely cause in 1 line 2) Evidence in 2 bullets 3) Fix in 3 steps.",
        "Max 150 words. No guessing beyond data. If SSL days<14 mention it first.",
    ]))
    story.append(h3("Prompt 2 — draft-update"))
    story.append(code_block([
        "Write a {tone} 2-sentence customer status update for {site} down {mins} mins.",
        "Cause: {ai_cause}. Include: we know, ETA, next update time. No jargon.",
    ]))
    story.append(callout("SAVE QUOTA — 3 RULES",
        "1) Cache 24h. 2) Never call in scheduler loop — only on click. 3) If 429, return cached or 'AI busy' — never crash incident. Weekly report = 1 call/week. This keeps you in free tier even with 50 demo clicks.",
        bg=AMBER_BG, border=HexColor("#FCD34A"), title_color="#92400E"))

    # ================= 14 =================
    story.append(section("14", "Timeline + Resume + Interview"))
    story.append(h2("8-week plan (10–12 hrs/week)"))
    story.append(styled_table(
        ["Week", "Do", "Show"],
        [
            ["1", "Phase 0–1: setup + auth", "Login works, tests 8 green"],
            ["2", "Phase 2: monitors CRUD", "Dashboard lists monitors"],
            ["3", "Phase 3: worker live", "Real checks saving every min"],
            ["4", "Phase 4–5: alerts + status", "Discord alert video"],
            ["5", "Phase 6: AI", "Explain button demo"],
            ["6", "Phase 7–8: keys + tests", "Coverage 80% badge"],
            ["7", "Phase 9: Docker + CI/CD", "Prod /health ok"],
            ["8", "Phase 10: polish + apply", "README + Loom + 20 applications"],
        ], [16*mm, 64*mm, 78*mm]
    ))
    story.append(h2("Resume bullets — copy these after build"))
    story.extend(bullets([
        "Built multi-tenant uptime SaaS monitoring URLs every minute with <b>FastAPI async + ARQ workers + Redis queue</b>; p95 check &lt;600ms, flap-safe alerting.",
        "Designed append-only <b>Postgres checks table (BRIN index, 90-day retention)</b> + Redis cache/pub-sub for live dashboard via WebSockets; public status pages cached 30s.",
        "Integrated <b>Gemini Flash RAG</b> for root-cause + post-mortems with 24h cache (90% fewer AI calls); shipped <b>Docker + GitHub Actions CI (80% pytest)</b> to Render/Vercel for $0.",
    ]))
    story.append(h2("Interview answers — memorize"))
    story.extend(bullets([
        "<b>'How avoid double alerts with 2 workers?'</b> → Redis distributed lock per monitor + idempotent incident check (only if no OPEN exists).",
        "<b>'Checks table huge?'</b> → BRIN on time, filter by monitor+range, paginate, delete >90d via cron, never full JOIN.",
        "<b>'Gemini slow/429?'</b> → Async worker + 20s timeout + cache 24h + graceful fallback, API never blocks.",
        "<b>'Public page viral traffic?'</b> → Cached 30s in Redis, no auth DB hit, rate-limited subscribe, static badge.",
        "<b>'How do you know deploy broke site?'</b> → Deploy markers overlay on latency graph + AI correlates spike after marker.",
    ]))
    story.append(Spacer(1,4*mm))
    story.append(callout("NEXT STEP WHEN YOU SAY 'GO'",
        "We start <b>Phase 0</b>: uv init + docker-compose + /health + first commit. I will give exact commands + files one by one. Reply <b>'start Phase 0'</b> when ready.",
        bg=PURPLE_BG, border=HexColor("#C4B5FD"), title_color="#5B21B6"))
    story.append(Spacer(1,4*mm))
    story.append(Paragraph("PulseTrack AI — Built to get you hired. Keep it simple, ship every week, show live links. Good luck.", sCaption))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUT

if __name__ == "__main__":
    path = build()
    print(f"PDF_OK:{path}")
    print(f"SIZE:{os.path.getsize(path)} bytes")
