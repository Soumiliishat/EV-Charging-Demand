import streamlit as st
import pandas as pd
import numpy as np
import pickle
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_option_menu import option_menu
from streamlit_folium import st_folium
import sqlite3
import os
import qrcode
from PIL import Image
from pathlib import Path
import base64
 
# ─────────────────────────────────────────
# SQLITE HELPERS  (replaces MySQL helpers)
# ───────────────────────────────────────── 
DB_PATH = "ev_project.db"   # SQLite file — no server needed, works on Streamlit Cloud
 
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
 
def read_sql_df(query, params=None):
    conn = get_connection()
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()
 
def execute_sql(query, values=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, values or [])
        conn.commit()
    finally:
        cursor.close()
        conn.close()
 
def init_database():
    conn = get_connection()
    cursor = conn.cursor()
 
    # SQLite uses INTEGER PRIMARY KEY AUTOINCREMENT  (not INT AUTO_INCREMENT)
    # SQLite uses TEXT  instead of VARCHAR(255)
    cursor.execute("""
CREATE TABLE IF NOT EXISTS ev_bunks (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    bunk_name        TEXT UNIQUE,
    owner_name       TEXT,
    state            TEXT,
    city             TEXT,
    address          TEXT,
    total_machines   INTEGER DEFAULT 0,
    fast_chargers    INTEGER DEFAULT 0,
    normal_chargers  INTEGER DEFAULT 0,
    damaged_machines INTEGER DEFAULT 0,
    working_machines INTEGER DEFAULT 0,
    contact          TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
 
    cursor.execute("""
CREATE TABLE IF NOT EXISTS slot_bookings (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    bunk_name        TEXT,
    customer_name    TEXT,
    phone            TEXT,
    vehicle_type     TEXT,
    slot_date        DATE,
    slot_time        TIME,
    charging_type    TEXT,
    estimated_price  REAL,
    advance_amount   REAL,
    payment_method   TEXT,
    payment_status   TEXT DEFAULT 'Pending',
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
 
    cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT UNIQUE NOT NULL,
    password   TEXT NOT NULL,
    full_name  TEXT,
    email      TEXT,
    role       TEXT DEFAULT 'User',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
 
    conn.commit()
    cursor.close()
    conn.close()
 
 
# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Chargevo | EV Charging Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed"
)
 
# ─────────────────────────────────────────
# GLOBAL CSS  — Professional Dark-Luxury Theme
# ─────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
 
<style>
/* ── Reset & root ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
 
:root {
    --teal:    #00E5B8;
    --teal-dk: #00B896;
    --sky:     #38C8F8;
    --bg:      #04080F;
    --bg2:     #080E1A;
    --bg3:     #0C1424;
    --card:    rgba(10,18,32,0.90);
    --border:  rgba(0,229,184,0.18);
    --border2: rgba(255,255,255,0.07);
    --text:    #E8EEF6;
    --muted:   #8BA0BA;
    --danger:  #FF4B6B;
    --warn:    #F59E0B;
    --success: #22D3A0;
    --radius:  16px;
    --radius2: 24px;
    --font-h:  'Syne', sans-serif;
    --font-b:  'DM Sans', sans-serif;
}
 
/* ── Full app background with image support ── */
[data-testid="stAppViewContainer"] {
    background-image:
        radial-gradient(ellipse 80% 50% at 20% -10%, rgba(0,229,184,0.09) 0%, transparent 55%),
        radial-gradient(ellipse 60% 40% at 80% 110%, rgba(56,200,248,0.07) 0%, transparent 55%),
        linear-gradient(170deg, rgba(4,8,15,0.97) 0%, rgba(6,12,24,0.95) 100%),
        url("https://images.unsplash.com/photo-1593941707882-a5bba14938c7?w=1920&q=80");
    background-size: cover;
    background-attachment: fixed;
    background-position: center;
    font-family: var(--font-b);
}
[data-testid="stMain"] {
    background: transparent !important;
    font-family: var(--font-b);
}
 
[data-testid="stSidebar"]       { display: none !important; }
[data-testid="stHeader"]        { background: transparent !important; }
[data-testid="stDecoration"]    { display: none !important; }
footer                          { display: none !important; }
 
.block-container {
    padding: 1.5rem 3rem 4rem !important;
    max-width: 1400px !important;
}
 
/* ── Typography ── */
h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-h) !important;
    color: var(--text) !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}
p, label, span, div, li {
    font-family: var(--font-b) !important;
    color: var(--text) !important;
}
.stMarkdown p { color: var(--muted) !important; }
 
/* ── Streamlit header tag overrides ── */
[data-testid="stHeading"] h1,
[data-testid="stHeading"] h2,
[data-testid="stHeading"] h3 {
    color: var(--text) !important;
}
 
/* ── Inputs ── */
[data-baseweb="select"] > div,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input,
textarea,
[data-testid="stDateInput"] input,
[data-baseweb="input"] input {
    background: var(--bg3) !important;
    color: var(--text) !important;
    border: 1px solid var(--border2) !important;
    border-radius: 12px !important;
    font-family: var(--font-b) !important;
    transition: border-color 0.2s;
}
[data-baseweb="select"] > div:focus-within,
[data-testid="stTextInput"] input:focus,
textarea:focus {
    border-color: var(--teal) !important;
    box-shadow: 0 0 0 3px rgba(0,229,184,0.12) !important;
}
[data-baseweb="select"] svg { color: var(--teal) !important; }

/* ── Placeholder text — visible in both light & dark mode ── */
[data-testid="stTextInput"] input::placeholder,
[data-testid="stNumberInput"] input::placeholder,
[data-testid="stDateInput"] input::placeholder,
[data-baseweb="input"] input::placeholder,
textarea::placeholder {
    color: #8BA0BA !important;
    opacity: 1 !important;
}
/* WebKit browsers */
[data-testid="stTextInput"] input::-webkit-input-placeholder,
[data-testid="stNumberInput"] input::-webkit-input-placeholder,
[data-baseweb="input"] input::-webkit-input-placeholder,
textarea::-webkit-input-placeholder {
    color: #8BA0BA !important;
    opacity: 1 !important;
}
/* Firefox */
[data-testid="stTextInput"] input::-moz-placeholder,
[data-testid="stNumberInput"] input::-moz-placeholder,
[data-baseweb="input"] input::-moz-placeholder,
textarea::-moz-placeholder {
    color: #8BA0BA !important;
    opacity: 1 !important;
}
 
/* ── Buttons ── */
.stButton > button,
.stDownloadButton > button {
    width: 100%;
    height: 48px;
    border-radius: 12px;
    font-family: var(--font-h) !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    letter-spacing: 0.02em;
    border: none !important;
    color: #04080F !important;
    background: linear-gradient(135deg, var(--teal) 0%, var(--sky) 100%) !important;
    box-shadow: 0 4px 20px rgba(0,229,184,0.25) !important;
    transition: transform 0.2s, box-shadow 0.2s !important;
}
.stButton > button:hover,
.stDownloadButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(0,229,184,0.40) !important;
}
/* Secondary (inactive role) button — outlined style */
.stButton > button[kind="secondary"] {
    background: rgba(0,229,184,0.05) !important;
    border: 1px solid rgba(0,229,184,0.25) !important;
    color: #8BA0BA !important;
    box-shadow: none !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(0,229,184,0.10) !important;
    border-color: rgba(0,229,184,0.45) !important;
    color: #00E5B8 !important;
    transform: none !important;
}
/* Second column red button override (Cancel / Delete) */
div[data-testid="column"]:nth-of-type(2) .stButton > button {
    background: linear-gradient(135deg, #FF4B6B, #DC2626) !important;
    color: white !important;
    box-shadow: 0 4px 20px rgba(255,75,107,0.25) !important;
}
 
/* ── Metrics ── */
[data-testid="metric-container"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 20px 22px !important;
    backdrop-filter: blur(20px);
    box-shadow: 0 4px 30px rgba(0,229,184,0.08);
    transition: transform 0.2s, box-shadow 0.2s;
}
[data-testid="metric-container"]:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 40px rgba(0,229,184,0.15);
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    color: var(--muted) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--teal) !important;
    font-family: var(--font-h) !important;
    font-size: 28px !important;
    font-weight: 800 !important;
}
 
/* ── Alerts ── */
[data-testid="stAlert"] {
    border-radius: var(--radius) !important;
    border-left-width: 4px !important;
    background: rgba(10,18,32,0.85) !important;
    backdrop-filter: blur(12px);
}
 
/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border-radius: var(--radius) !important;
    overflow: hidden;
    border: 1px solid var(--border2) !important;
}
 
/* ── Slider ── */
[data-testid="stSlider"] [role="slider"] {
    background: var(--teal) !important;
}
[data-testid="stSlider"] [data-testid="stSliderTrack"] > div:first-child {
    background: var(--teal) !important;
}
 
/* ── Divider ── */
hr { border-color: var(--border2) !important; margin: 2rem 0 !important; }
 
/* ── Option menu override ── */
nav[style] { font-family: var(--font-b) !important; }
 
/* ────────────────── CUSTOM COMPONENTS ────────────────── */
 
/* -- Glassmorphism card -- */
.g-card {
    background: var(--card);
    backdrop-filter: blur(24px);
    border: 1px solid var(--border);
    border-radius: var(--radius2);
    padding: 28px 32px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.40), inset 0 1px 0 rgba(255,255,255,0.04);
    position: relative;
    overflow: hidden;
}
.g-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,229,184,0.5), transparent);
}
 
/* -- Pill badge -- */
.pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 14px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.pill-teal { background: rgba(0,229,184,0.12); color: var(--teal); border: 1px solid rgba(0,229,184,0.25); }
.pill-red  { background: rgba(255,75,107,0.12); color: var(--danger); border: 1px solid rgba(255,75,107,0.25); }
.pill-warn { background: rgba(245,158,11,0.12); color: var(--warn);   border: 1px solid rgba(245,158,11,0.25); }
 
/* -- Section label -- */
.section-label {
    font-family: var(--font-h);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--teal);
    margin-bottom: 10px;
}
 
/* -- Page title block -- */
.page-title-wrap {
    margin-bottom: 2.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border2);
}
.page-title {
    font-family: var(--font-h);
    font-size: 42px;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -0.03em;
    line-height: 1.1;
}
.page-sub {
    color: var(--muted);
    font-size: 16px;
    margin-top: 8px;
    font-weight: 400;
}
 
/* -- Hero banner -- */
.hero-wrap {
    position: relative;
    border-radius: var(--radius2);
    overflow: hidden;
    padding: 90px 60px 100px;
    margin-bottom: 2rem;
    background:
        linear-gradient(135deg, rgba(0,229,184,0.10) 0%, rgba(56,200,248,0.06) 100%),
        var(--bg2);
    border: 1px solid var(--border);
    box-shadow: 0 8px 60px rgba(0,0,0,0.5);
    text-align: center;
}
.hero-grid {
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(0,229,184,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,229,184,0.04) 1px, transparent 1px);
    background-size: 48px 48px;
}
.hero-badge {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 999px;
    background: rgba(0,229,184,0.10);
    border: 1px solid rgba(0,229,184,0.28);
    color: var(--teal);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 20px;
}
.hero-title {
    font-family: var(--font-h);
    font-size: 60px;
    font-weight: 800;
    color: white;
    line-height: 1.05;
    letter-spacing: -0.04em;
}
.hero-title span { color: var(--teal); }
.hero-sub {
    color: var(--muted);
    font-size: 18px;
    margin-top: 14px;
    max-width: 560px;
    margin-left: auto;
    margin-right: auto;
    line-height: 1.7;
}
 
/* -- Stat card (big number) -- */
.stat-card {
    background: var(--card);
    border: 1px solid var(--border2);
    border-radius: var(--radius2);
    padding: 28px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: transform 0.25s, border-color 0.25s, box-shadow 0.25s;
}
.stat-card:hover {
    transform: translateY(-5px);
    border-color: var(--border);
    box-shadow: 0 12px 50px rgba(0,229,184,0.12);
}
.stat-card .icon {
    font-size: 28px;
    margin-bottom: 12px;
    display: block;
}
.stat-card .number {
    font-family: var(--font-h);
    font-size: 38px;
    font-weight: 800;
    color: var(--teal);
    line-height: 1;
}
.stat-card .label {
    color: var(--muted);
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 8px;
}
.stat-card .stripe {
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--teal), var(--sky));
    border-radius: 0 0 var(--radius2) var(--radius2);
}
 
/* -- Demand highlight card -- */
.demand-card {
    border-radius: var(--radius2);
    padding: 30px;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s;
}
.demand-card:hover { transform: translateY(-4px); }
.demand-card-high {
    background: linear-gradient(135deg, rgba(255,75,107,0.15), rgba(220,38,38,0.08));
    border: 1px solid rgba(255,75,107,0.25);
}
.demand-card-low {
    background: linear-gradient(135deg, rgba(0,229,184,0.15), rgba(34,211,160,0.08));
    border: 1px solid rgba(0,229,184,0.25);
}
.demand-card h3 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 10px; }
.demand-card .d-state { font-family: var(--font-h); font-size: 30px; font-weight: 800; color: white; }
.demand-card .d-val  { font-size: 15px; margin-top: 6px; }
.demand-card-high h3, .demand-card-high .d-val { color: #FF8BA0; }
.demand-card-low  h3, .demand-card-low  .d-val  { color: var(--teal); }
 
/* -- Marquee ticker -- */
.ticker-wrap {
    width: 100%;
    overflow: hidden;
    background: rgba(0,229,184,0.04);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 0;
    margin: 1.5rem 0;
}
.ticker-inner {
    display: inline-block;
    white-space: nowrap;
    padding-left: 100%;
    animation: scroll-ticker 30s linear infinite;
    color: var(--muted);
    font-size: 14px;
    font-weight: 500;
    letter-spacing: 0.02em;
}
.ticker-inner .sep { color: var(--teal); margin: 0 20px; }
@keyframes scroll-ticker {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-100%); }
}
 
/* -- Team card -- */
.team-card {
    background: var(--card);
    border: 1px solid var(--border2);
    border-radius: var(--radius2);
    padding: 30px 24px;
    text-align: center;
    transition: transform 0.25s, border-color 0.25s, box-shadow 0.25s;
    height: 340px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
}
.team-card:hover {
    transform: translateY(-6px);
    border-color: var(--border);
    box-shadow: 0 16px 50px rgba(0,229,184,0.12);
}
.team-avatar {
    width: 80px; height: 80px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--teal), var(--sky));
    display: flex; align-items: center; justify-content: center;
    font-family: var(--font-h);
    font-size: 30px; font-weight: 800;
    color: #04080F;
    margin-bottom: 18px;
    box-shadow: 0 8px 30px rgba(0,229,184,0.30);
}
.team-name { font-family: var(--font-h); font-size: 20px; font-weight: 700; color: white; }
.team-role { color: var(--teal); font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; margin-top: 6px; }
.team-desc { color: var(--muted); font-size: 14px; line-height: 1.7; margin-top: 12px; }
 
/* -- About card -- */
.about-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius2);
    padding: 28px 32px;
    box-shadow: 0 4px 30px rgba(0,0,0,0.3);
    margin-bottom: 1.2rem;
    position: relative;
    overflow: hidden;
}
.about-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, var(--teal), transparent);
}
.about-card-title {
    font-family: var(--font-h);
    font-size: 20px; font-weight: 700;
    color: var(--teal);
    margin-bottom: 12px;
}
.about-card-text { color: var(--muted); font-size: 15px; line-height: 1.8; }
.about-card-text br + br { margin-top: 6px; }
 
/* -- Tech chip -- */
.tech-row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 1rem; }
.tech-chip {
    padding: 8px 20px;
    border-radius: 999px;
    background: rgba(0,229,184,0.07);
    border: 1px solid rgba(0,229,184,0.20);
    color: var(--teal);
    font-size: 14px; font-weight: 600;
    letter-spacing: 0.04em;
    transition: background 0.2s, transform 0.2s;
}
.tech-chip:hover { background: rgba(0,229,184,0.15); transform: translateY(-2px); }
 
/* -- Contact card -- */
.contact-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius2);
    padding: 32px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.30);
}
.contact-item { display: flex; align-items: center; gap: 14px; padding: 14px 0; border-bottom: 1px solid var(--border2); }
.contact-item:last-child { border-bottom: none; }
.contact-icon { font-size: 22px; width: 44px; height: 44px; border-radius: 12px; background: rgba(0,229,184,0.10); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.contact-label { color: var(--muted); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; }
.contact-val { color: var(--text); font-size: 15px; font-weight: 500; }
 
/* -- Footer -- */
.footer-wrap {
    background: var(--bg2);
    border: 1px solid var(--border2);
    border-radius: var(--radius2);
    padding: 40px;
    margin-top: 3rem;
}
.footer-brand { font-family: var(--font-h); font-size: 22px; font-weight: 800; color: white; letter-spacing: -0.02em; }
.footer-brand span { color: var(--teal); }
.footer-tagline { color: var(--muted); font-size: 14px; line-height: 1.7; margin-top: 10px; max-width: 200px; }
.footer-col-title { font-family: var(--font-h); font-size: 14px; font-weight: 700; color: var(--text); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 14px; }
.footer-link { color: var(--muted); font-size: 14px; line-height: 2.0; display: block; transition: color 0.2s; }
.footer-link:hover { color: var(--teal); }
.footer-divider { border-color: var(--border2); margin: 28px 0; }
.footer-copy { color: #4B6080; font-size: 13px; text-align: center; }
 
/* -- Header wrapper -- */
.header-wrap {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 32px;
    background: rgba(8,14,26,0.80);
    backdrop-filter: blur(24px);
    border: 1px solid var(--border2);
    border-radius: var(--radius2);
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 30px rgba(0,0,0,0.30);
}
.header-logo-text {
    font-family: var(--font-h);
    font-size: 26px;
    font-weight: 800;
    color: white;
    letter-spacing: -0.03em;
}
.header-logo-text span { color: var(--teal); }
 
/* -- Prediction result -- */
.pred-result-wrap {
    background: linear-gradient(135deg, rgba(0,229,184,0.08), rgba(56,200,248,0.05));
    border: 1px solid var(--border);
    border-radius: var(--radius2);
    padding: 28px 32px;
    margin-top: 1.5rem;
}
 
/* -- Machine status badge -- */
.machine-badge {
    display: inline-block;
    padding: 6px 18px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 700;
}
.badge-excellent { background: rgba(34,211,160,0.15); color: #22D3A0; border: 1px solid rgba(34,211,160,0.30); }
.badge-good      { background: rgba(96,165,250,0.12); color: #60A5FA; border: 1px solid rgba(96,165,250,0.25); }
.badge-moderate  { background: rgba(245,158,11,0.12); color: #F59E0B; border: 1px solid rgba(245,158,11,0.25); }
.badge-poor      { background: rgba(251,113,33,0.12); color: #FB7121; border: 1px solid rgba(251,113,33,0.25); }
.badge-critical  { background: rgba(239,68,68,0.12); color: #EF4444; border: 1px solid rgba(239,68,68,0.25); }
 
/* -- Admin sub-nav -- */
.admin-subnav {
    background: rgba(12,20,36,0.85);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    padding: 6px;
    margin-bottom: 1.5rem;
}

/* ── Extra premium organization fixes ── */
.brand-card{
    display:flex; align-items:center; gap:18px;
    background:linear-gradient(135deg,rgba(8,14,26,.92),rgba(0,229,184,.06));
    border:1px solid rgba(0,229,184,.22);
    border-radius:24px;
    padding:18px 22px;
    margin:0 auto 22px auto;
    box-shadow:0 18px 55px rgba(0,0,0,.42);
}
.brand-logo{width:92px;height:92px;border-radius:18px;object-fit:cover;box-shadow:0 8px 28px rgba(0,0,0,.35);}
.brand-title{font-family:var(--font-h);font-size:42px;font-weight:900;color:white;line-height:1;margin:0;}
.brand-title span{color:var(--teal);}
.brand-sub{color:var(--muted);font-size:14px;margin-top:8px;}
.demo-admin-box{
    background:rgba(0,229,184,.07);
    border:1px solid rgba(0,229,184,.24);
    border-radius:14px;
    padding:12px 14px;
    margin:12px 0 16px;
    color:#B8C7D9;
    font-size:13px;
}
.hero-actions-wrap{
    max-width:620px;
    margin:-7rem auto 3rem auto;
    position:relative;
    z-index:5;
}
.hero-actions-wrap .stButton>button{
    height:56px!important;
    border-radius:16px!important;
    font-size:16px!important;
    font-weight:900!important;
}
.header-panel{
    background:rgba(8,14,26,.72);
    border:1px solid rgba(0,229,184,.12);
    border-radius:24px;
    padding:16px 20px;
    margin-bottom:24px;
    box-shadow:0 14px 50px rgba(0,0,0,.28);
    backdrop-filter:blur(18px);
}
@media (max-width: 768px){
    .block-container{padding:1rem!important;}
    .brand-title{font-size:32px;}
    .brand-logo{width:74px;height:74px;}
    .hero-title{font-size:42px;}
    .hero-wrap{padding:70px 22px 120px;}
    .hero-actions-wrap{margin:-6rem auto 2rem auto;}
}



/* ============================================================
   FINAL FIX: KEEP APP DARK EVEN WHEN SYSTEM / STREAMLIT IS LIGHT
   This block must stay at the very END of the main CSS.
   ============================================================ */
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], .stApp {
    color-scheme: dark !important;
    background-color: #04080F !important;
    color: #E8EEF6 !important;
}

[data-testid="stAppViewContainer"] {
    background-image:
        radial-gradient(ellipse 80% 50% at 20% -10%, rgba(0,229,184,0.09) 0%, transparent 55%),
        radial-gradient(ellipse 60% 40% at 80% 110%, rgba(56,200,248,0.07) 0%, transparent 55%),
        linear-gradient(170deg, rgba(4,8,15,0.97) 0%, rgba(6,12,24,0.95) 100%),
        url("https://images.unsplash.com/photo-1593941707882-a5bba14938c7?w=1920&q=80") !important;
    background-size: cover !important;
    background-attachment: fixed !important;
    background-position: center !important;
}

/* Text fixed for light mode */
h1, h2, h3, h4, h5, h6, label,
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
p, span, div, li {
    color: #E8EEF6 !important;
    -webkit-text-fill-color: inherit !important;
}

/* Input boxes fixed dark */
[data-baseweb="select"] > div,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTimeInput"] input,
[data-baseweb="input"] input,
textarea,
input {
    background: #0C1424 !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    border: 1px solid rgba(232,238,246,0.75) !important;
    border-radius: 13px !important;
    caret-color: #00E5B8 !important;
    box-shadow: none !important;
}

/* Placeholder visible but dark-theme matching */
input::placeholder, textarea::placeholder,
[data-testid="stTextInput"] input::placeholder,
[data-testid="stNumberInput"] input::placeholder,
[data-baseweb="input"] input::placeholder {
    color: #8BA0BA !important;
    -webkit-text-fill-color: #8BA0BA !important;
    opacity: 1 !important;
}

/* Selected dropdown value fixed */
[data-baseweb="select"] span,
[data-baseweb="select"] div,
[data-baseweb="select"] svg {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    fill: #00E5B8 !important;
}

/* Remove tiny cursor/rectangle after selected dropdown text */
[data-baseweb="select"] input {
    opacity: 0 !important;
    color: transparent !important;
    -webkit-text-fill-color: transparent !important;
    caret-color: transparent !important;
    width: 0px !important;
    min-width: 0px !important;
}

/* Dropdown menu must stay dark, not white, in system light mode */
body div[data-baseweb="popover"],
body div[data-baseweb="popover"] > div,
body div[data-baseweb="menu"],
body ul[role="listbox"],
body [role="listbox"] {
    background: #07111F !important;
    color: #E8EEF6 !important;
    -webkit-text-fill-color: #E8EEF6 !important;
    border: 1px solid rgba(0,229,184,0.32) !important;
    border-radius: 14px !important;
    box-shadow: 0 24px 70px rgba(0,0,0,0.65) !important;
}

body div[data-baseweb="popover"] *,
body div[data-baseweb="menu"] *,
body ul[role="listbox"] *,
body [role="listbox"] *,
body li[role="option"],
body div[role="option"] {
    background: #07111F !important;
    color: #E8EEF6 !important;
    -webkit-text-fill-color: #E8EEF6 !important;
    opacity: 1 !important;
    font-weight: 700 !important;
    text-shadow: none !important;
}

body li[role="option"],
body div[role="option"] {
    padding: 10px 14px !important;
    min-height: 42px !important;
}

body li[role="option"]:hover,
body div[role="option"]:hover,
body [role="option"]:hover,
body li[aria-selected="true"],
body div[aria-selected="true"] {
    background: rgba(0,229,184,0.18) !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

/* Number input + - buttons fixed */
[data-testid="stNumberInput"] button {
    background: #E8EEF6 !important;
    color: #04080F !important;
    -webkit-text-fill-color: #04080F !important;
    border: 1px solid #CBD5E1 !important;
    font-weight: 900 !important;
}

/* Buttons fixed */
.stButton > button,
.stFormSubmitButton > button,
.stDownloadButton > button {
    background: linear-gradient(135deg,#00E5B8,#38C8F8) !important;
    color: #031018 !important;
    -webkit-text-fill-color: #031018 !important;
    border: 1px solid rgba(0,229,184,.55) !important;
    font-weight: 900 !important;
    opacity: 1 !important;
}

.stButton > button[kind="secondary"] {
    background: rgba(7,17,31,.88) !important;
    color: #DCEAF7 !important;
    -webkit-text-fill-color: #DCEAF7 !important;
    border: 1px solid rgba(0,229,184,.32) !important;
}

/* Cards fixed */
.g-card, .auth-card, .brand-card, .contact-card, .about-card,
.stat-card, .footer-wrap, .pred-result-wrap, .nav-shell {
    background: linear-gradient(135deg, rgba(7,17,31,.94), rgba(10,25,44,.90)) !important;
    border: 1px solid rgba(0,229,184,.26) !important;
    box-shadow: 0 18px 60px rgba(0,0,0,.38) !important;
}
</style>
""", unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────
# LOAD DATA & MODELS
# ─────────────────────────────────────────
try:
    df = pd.read_csv("final_ev_dataset_15000.csv")
except Exception:
    st.error("Dataset file not found: final_ev_dataset_15000.csv")
    st.stop()
 
try:
    model            = pickle.load(open("ev_model.pkl",               "rb"))
    encoder          = pickle.load(open("charging_type_encoder.pkl",  "rb"))
    features         = pickle.load(open("features.pkl",               "rb"))
    model_results    = pickle.load(open("model_results.pkl",           "rb"))
    feature_importance = pickle.load(open("feature_importance.pkl",   "rb"))
except Exception as e:
    st.error("Model files are missing. Please run train_model.py first.")
    st.write(e)
    st.stop()
 
 
# ─────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────
if "logged_in"        not in st.session_state: st.session_state.logged_in = False
if "role"             not in st.session_state: st.session_state.role      = None
if "payment_status"   not in st.session_state: st.session_state.payment_status = "Pending"
if "page"             not in st.session_state: st.session_state.page = "Home"


# ─────────────────────────────────────────
# FLOATING PROJECT CHATBOT
# ─────────────────────────────────────────
def get_chargevo_bot_answer(user_question, role="User"):
    """Simple rule-based chatbot for Chargevo project guidance."""
    q = (user_question or "").lower().strip()

    if not q:
        return "Please type your question. I can help with prediction, booking, payment, admin panel, analytics, and EV bunk management."

    greetings = ["hi", "hello", "hey", "good morning", "good evening"]
    if any(word in q for word in greetings):
        return f"Hello! I am Chargevo Assistant. You are logged in as {role}. Ask me about demand prediction, slot booking, payment, EV bunks, analytics, or how to use this project."

    if any(word in q for word in ["what is", "about project", "chargevo", "project", "purpose"]):
        return "Chargevo is an EV Charging Demand Prediction System. It helps users predict charging demand, find EV charging stations, book charging slots, estimate price, and helps admins manage EV bunk details and monitor analytics."

    if any(word in q for word in ["predict", "prediction", "forecast", "demand"]):
        return "Go to the Prediction page. Select State, City, Vehicle Type, Power, Total Machines, Damaged Machines, and electrical values. Then click the prediction button to get the estimated EV charging demand."

    if any(word in q for word in ["book", "slot", "booking", "reserve"]):
        return "Go to the Book Slot page. Select your State, City, EV Bunk, Date, Time, Vehicle Type, and Charging Type. Then complete the payment step to reserve your charging slot. If a slot is already booked, choose another time."

    if any(word in q for word in ["payment", "pay", "advance", "qr", "card", "paid"]):
        return "In the booking page, Chargevo shows total estimated price, advance amount, and remaining amount. You can choose QR payment or card payment. After payment, the booking status should show as Paid/Booked."

    if any(word in q for word in ["admin", "owner", "manage", "bunk", "station", "machine", "charger"]):
        if role == "Admin":
            return "As Admin, open Admin Panel. You can create a new EV bunk, update total machines, damaged machines, working machines, fast chargers, normal chargers, owner details, and contact information."
        return "Admin features are only available for the Admin profile. As a User, you can use Prediction, Book Slot, About Us, and Contact Us pages."

    if any(word in q for word in ["analytics", "dashboard", "chart", "graph", "report"]):
        if role == "Admin":
            return "Open the Analytics page to view charts, demand insights, state/city analysis, station performance, and project dashboard details."
        return "Analytics is available only for Admin. Users can view Prediction and Book Slot features."

    if any(word in q for word in ["model", "machine learning", "ml", "algorithm", "random forest"]):
        return "This project uses a machine learning model to predict EV charging demand from station, vehicle, location, charger, and electrical features. The model output helps plan charging resources better."

    if any(word in q for word in ["login", "register", "password", "profile", "user"]):
        return "New users can register first, then log in using username and password. Admin can log in using admin credentials. User and Admin profiles have different menu options."

    if any(word in q for word in ["contact", "help", "support"]):
        return "You can open the Contact Us page for project contact details. For using the app, ask me about prediction, booking, payment, admin panel, or analytics."

    if any(word in q for word in ["how to use", "steps", "guide", "work"]):
        if role == "Admin":
            return "Admin guide: 1) Check Home dashboard, 2) Use Prediction for demand forecast, 3) Use Analytics for insights, 4) Use Admin Panel to create/manage EV bunks, 5) Check Book Slot for reservations."
        return "User guide: 1) Open Prediction to check demand, 2) Open Book Slot to reserve charging, 3) Complete payment, 4) Use About Us and Contact Us for project details."

    return "I can help with Chargevo project questions like: how to predict demand, book a slot, make payment, manage EV bunks, use admin panel, view analytics, or understand the ML model. Please ask in simple words."


def render_floating_chatbot():
    """Floating chatbot button and chat panel for both Admin and User profiles."""
    if "chatbot_open" not in st.session_state:
        st.session_state.chatbot_open = False
    if "chatbot_messages" not in st.session_state:
        st.session_state.chatbot_messages = [
            {"role": "assistant", "text": "Hi! I am Chargevo Assistant. Ask me anything about this EV Charging project."}
        ]

    st.markdown("""
    <style>
    .st-key-chatbot_toggle {
        position: fixed !important;
        right: 28px !important;
        bottom: 28px !important;
        z-index: 999999 !important;
        width: 66px !important;
    }
    .st-key-chatbot_toggle button {
        width: 66px !important;
        height: 66px !important;
        border-radius: 50% !important;
        font-size: 28px !important;
        padding: 0 !important;
        background: linear-gradient(135deg,#00E5B8,#38C8F8) !important;
        color: #031018 !important;
        box-shadow: 0 16px 45px rgba(0,229,184,.45) !important;
        border: 1px solid rgba(255,255,255,.25) !important;
        animation: chatbotPulse 2.2s infinite;
    }
    @keyframes chatbotPulse {
        0% { box-shadow: 0 0 0 0 rgba(0,229,184,.45); }
        70% { box-shadow: 0 0 0 16px rgba(0,229,184,0); }
        100% { box-shadow: 0 0 0 0 rgba(0,229,184,0); }
    }
    .st-key-chatbot_panel {
        position: fixed !important;
        right: 28px !important;
        bottom: 105px !important;
        width: 380px !important;
        max-width: calc(100vw - 35px) !important;
        max-height: 620px !important;
        overflow-y: auto !important;
        z-index: 999998 !important;
        background: linear-gradient(145deg, rgba(7,17,31,.98), rgba(10,25,44,.96)) !important;
        border: 1px solid rgba(0,229,184,.35) !important;
        border-radius: 24px !important;
        padding: 18px !important;
        box-shadow: 0 24px 80px rgba(0,0,0,.65) !important;
        backdrop-filter: blur(22px) !important;
        animation: chatbotSlideUp .28s ease-out;
    }
    @keyframes chatbotSlideUp {
        from { opacity: 0; transform: translateY(18px) scale(.96); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }
    .chatbot-head {
        display:flex; align-items:center; justify-content:space-between;
        padding-bottom:12px; border-bottom:1px solid rgba(255,255,255,.08); margin-bottom:12px;
    }
    .chatbot-title {font-family:'Syne',sans-serif;font-size:18px;font-weight:900;color:white;}
    .chatbot-role {font-size:11px;color:#00E5B8;font-weight:800;text-transform:uppercase;letter-spacing:.08em;}
    .bot-msg, .user-msg {
        padding:10px 12px; border-radius:16px; margin:8px 0; font-size:14px; line-height:1.55;
    }
    .bot-msg {background:rgba(0,229,184,.10); border:1px solid rgba(0,229,184,.18); color:#DFFDF6; border-bottom-left-radius:5px;}
    .user-msg {background:rgba(56,200,248,.12); border:1px solid rgba(56,200,248,.18); color:#EAF8FF; border-bottom-right-radius:5px; margin-left:38px;}
    .chatbot-hint {font-size:12px;color:#8BA0BA;margin:8px 0 10px;line-height:1.5;}
    @media(max-width: 600px){
        .st-key-chatbot_panel {right: 12px !important; bottom: 92px !important; width: calc(100vw - 24px) !important;}
        .st-key-chatbot_toggle {right: 18px !important; bottom: 18px !important;}
    }
    </style>
    """, unsafe_allow_html=True)

    if st.button("💬", key="chatbot_toggle", help="Open Chargevo Assistant"):
        st.session_state.chatbot_open = not st.session_state.chatbot_open
        st.rerun()

    if st.session_state.chatbot_open:
        with st.container(key="chatbot_panel"):
            st.markdown(f"""
            <div class="chatbot-head">
                <div>
                    <div class="chatbot-title">⚡ Chargevo Assistant</div>
                    <div class="chatbot-role">{st.session_state.role} Profile Support</div>
                </div>
                <div style="font-size:22px;">🤖</div>
            </div>
            <div class="chatbot-hint">Ask about prediction, booking, payment, admin panel, EV bunk, analytics, or model working.</div>
            """, unsafe_allow_html=True)

            for msg in st.session_state.chatbot_messages[-8:]:
                css_class = "user-msg" if msg["role"] == "user" else "bot-msg"
                name = "You" if msg["role"] == "user" else "Bot"
                safe_text = str(msg["text"]).replace("<", "&lt;").replace(">", "&gt;")
                st.markdown(f'<div class="{css_class}"><b>{name}:</b> {safe_text}</div>', unsafe_allow_html=True)

            with st.form("chargevo_chatbot_form", clear_on_submit=True):
                user_q = st.text_input("Ask your question", placeholder="Example: How can I book a charging slot?", label_visibility="collapsed")
                send = st.form_submit_button("Send ➤", use_container_width=True)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("Clear Chat", key="clear_chatbot", use_container_width=True):
                    st.session_state.chatbot_messages = [
                        {"role": "assistant", "text": "Chat cleared. How can I help you with Chargevo?"}
                    ]
                    st.rerun()
            with c2:
                if st.button("Close", key="close_chatbot", use_container_width=True):
                    st.session_state.chatbot_open = False
                    st.rerun()

            if send and user_q.strip():
                st.session_state.chatbot_messages.append({"role": "user", "text": user_q.strip()})
                answer = get_chargevo_bot_answer(user_q, st.session_state.role)
                st.session_state.chatbot_messages.append({"role": "assistant", "text": answer})
                st.rerun()
 
 
# ─────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────
def _ensure_users_table():
    """SQLite users table for Streamlit Cloud. No MySQL server needed."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            email TEXT UNIQUE,
            role TEXT DEFAULT 'User',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def _register_user(username, password, full_name, email):
    _ensure_users_table()
    try:
        execute_sql(
            """
            INSERT INTO users (full_name, email, username, password, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (full_name.strip(), email.strip(), username.strip(), password, "User")
        )
        return True, "Account created successfully! Please log in now."
    except sqlite3.IntegrityError:
        return False, "Username or email already exists."
    except Exception as e:
        return False, f"Registration failed: {e}"


def _verify_user(username, password):
    _ensure_users_table()
    try:
        df_u = read_sql_df(
            """
            SELECT * FROM users
            WHERE username = ? AND password = ? AND LOWER(role) = 'user'
            """,
            (username.strip(), password)
        )
        return not df_u.empty
    except Exception:
        return False


# Intro and auth state
if "intro_done" not in st.session_state: st.session_state.intro_done = False
if "auth_mode" not in st.session_state: st.session_state.auth_mode = "login"


def _video_base64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


def _image_base64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def intro_page():
    """Full-screen splash video. Clicking Enter App opens the auth page."""
    st.markdown("""
    <style>
    .block-container {padding:0 !important; max-width:100% !important;}
    [data-testid="stHeader"], footer {display:none !important;}
    .intro-shell{position:fixed; inset:0; overflow:hidden; background:#020712;}
    .intro-video{position:absolute; inset:0; width:100vw; height:100vh; object-fit:contain; background:#020712;}
    .intro-overlay{position:absolute; inset:0; background:linear-gradient(90deg,rgba(2,7,18,.72),rgba(2,7,18,.18),rgba(2,7,18,.72));}
    .intro-content{position:fixed; z-index:2; inset:0; min-height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:30px;}
    .intro-badge{padding:8px 18px; border-radius:999px; background:rgba(0,229,184,.12); border:1px solid rgba(0,229,184,.32); color:#00E5B8; font-weight:800; letter-spacing:.10em; font-size:12px; text-transform:uppercase;}
    .intro-title{font-family:'Syne',sans-serif; font-size:70px; line-height:1.05; font-weight:900; color:white; margin:18px 0 12px; letter-spacing:-.05em;}
    .intro-title span{color:#00E5B8;}
    .intro-sub{color:#B8C7D9; font-size:18px; max-width:720px; line-height:1.7; margin-bottom:32px;}
    /* Center only one Enter App button over the video */
    .stButton{position:fixed !important; left:50% !important; top:85% !important; transform:translateX(-50%) !important; z-index:10 !important; width:230px !important;}
    .stButton>button{height:56px !important; border-radius:999px !important; font-weight:900 !important; font-size:17px !important; border:1px solid rgba(0,229,184,.45) !important; background:linear-gradient(135deg,#00E5B8,#38C8F8) !important; color:#020712 !important; box-shadow:0 12px 40px rgba(0,229,184,.34) !important;}
    @media (max-width: 768px){
        .intro-title{font-size:48px;}
        .intro-sub{font-size:15px;}
        .stButton{top:72% !important; width:210px !important;}
    }
    </style>
    """, unsafe_allow_html=True)

    v64 = _video_base64("ev_intro.mp4")
    if v64:
        video_html = f'<video class="intro-video" autoplay muted loop playsinline><source src="data:video/mp4;base64,{v64}" type="video/mp4"></video>'
    else:
        video_html = '<div class="intro-video" style="background:radial-gradient(circle at center,rgba(0,229,184,.18),transparent 45%),linear-gradient(135deg,#020712,#071827);"></div>'

    st.markdown(f"""
    <div class="intro-shell">
        {video_html}
        <div class="intro-overlay"></div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 Enter App", key="intro_enter_app", use_container_width=True):
        st.session_state.intro_done = True
        st.session_state.auth_mode = "login"
        st.rerun()


def login_page():
    _ensure_users_table()
    st.markdown("""
    <style>
    .block-container {padding-top:2.2rem !important; max-width:560px !important;}
    .auth-card{background:rgba(8,14,26,.88); border:1px solid rgba(0,229,184,.20); border-radius:24px; padding:22px 26px; box-shadow:0 18px 60px rgba(0,0,0,.45); backdrop-filter:blur(22px); margin-bottom:18px;}
    .auth-title{text-align:center;font-family:'Syne',sans-serif;font-size:36px;font-weight:900;color:white;letter-spacing:-.04em;margin:8px 0 2px;}
    .auth-title span{color:#00E5B8;}.auth-sub{text-align:center;color:#8BA0BA;font-size:14px;margin-bottom:18px;}
    .switch-box{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:10px 0 22px;}
    </style>
    """, unsafe_allow_html=True)

    logo_b64 = _image_base64("logo_EV.jpeg")
    if logo_b64:
        st.markdown(f"""
        <div class="brand-card">
            <img src="data:image/jpeg;base64,{logo_b64}" class="brand-logo">
            <div>
                <div class="brand-title">Charge<span>vo</span></div>
                <div class="brand-sub">EV Charging Intelligence Platform</div>
                <div class="brand-sub" style="font-size:12px;color:#6F86A6;margin-top:4px;">Secure Access Portal</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="brand-card">
            <div style="width:92px;height:92px;border-radius:18px;background:linear-gradient(135deg,#00E5B8,#38C8F8);display:flex;align-items:center;justify-content:center;font-size:42px;">⚡</div>
            <div>
                <div class="brand-title">Charge<span>vo</span></div>
                <div class="brand-sub">EV Charging Intelligence Platform</div>
                <div class="brand-sub" style="font-size:12px;color:#6F86A6;margin-top:4px;">Secure Access Portal</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    sw1, sw2 = st.columns(2)
    with sw1:
        if st.button("🔐 Log In", key="switch_login", use_container_width=True, type="primary" if st.session_state.auth_mode=="login" else "secondary"):
            st.session_state.auth_mode = "login"; st.rerun()
    with sw2:
        if st.button("✨ Register", key="switch_register", use_container_width=True, type="primary" if st.session_state.auth_mode=="register" else "secondary"):
            st.session_state.auth_mode = "register"; st.rerun()

    if st.session_state.auth_mode == "login":
        st.markdown('<div class="section-label">Login As</div>', unsafe_allow_html=True)
        if "login_role" not in st.session_state: st.session_state.login_role = "User"
        r1, r2 = st.columns(2)
        with r1:
            if st.button("👤 User", key="role_user_btn", use_container_width=True, type="primary" if st.session_state.login_role=="User" else "secondary"):
                st.session_state.login_role="User"; st.rerun()
        with r2:
            if st.button("🛡 Admin", key="role_admin_btn", use_container_width=True, type="primary" if st.session_state.login_role=="Admin" else "secondary"):
                st.session_state.login_role="Admin"; st.rerun()

        if st.session_state.login_role == "Admin":
            st.markdown("""
            <div class="demo-admin-box">
                <b style="color:#00E5B8;">🔐 Demo Admin Login</b><br>
                Username: <b>admin</b> &nbsp; | &nbsp; Password: <b>admin123</b>
            </div>
            """, unsafe_allow_html=True)

        li_username = st.text_input("Username", placeholder="Enter username", key="li_username")
        li_password = st.text_input("Password", type="password", placeholder="Enter password", key="li_password")
        c1, c2 = st.columns(2)
        with c1:
            login_btn = st.button("🚀 Log In", use_container_width=True, key="login_btn")
        with c2:
            back_btn = st.button("⬅ Intro", use_container_width=True, key="back_intro_btn")
        if back_btn:
            st.session_state.intro_done=False; st.rerun()
        if login_btn:
            role = st.session_state.login_role
            if role == "Admin" and li_username == "admin" and li_password == "admin123":
                st.session_state.logged_in=True; st.session_state.role="Admin"; st.rerun()
            elif role == "User" and (_verify_user(li_username, li_password) or (li_username == "user" and li_password == "user123")):
                st.session_state.logged_in=True; st.session_state.role="User"; st.rerun()
            else:
                st.error("❌ Invalid credentials. New user? Please Register first.")
    else:
        st.info("👋 First time here? Create your account below.")
        reg_fullname = st.text_input("Full Name", placeholder="Your full name", key="reg_fullname")
        reg_email = st.text_input("Email Address", placeholder="your@email.com", key="reg_email")
        reg_username = st.text_input("Choose Username", placeholder="Pick a unique username", key="reg_username")
        reg_pw1 = st.text_input("Password", type="password", placeholder="Create a password", key="reg_pw1")
        reg_pw2 = st.text_input("Confirm Password", type="password", placeholder="Re-enter password", key="reg_pw2")
        c1, c2 = st.columns(2)
        with c1:
            reg_btn = st.button("🚀 Create Account", use_container_width=True, key="register_btn")
        with c2:
            back_btn = st.button("⬅ Intro", use_container_width=True, key="reg_back_intro_btn")
        if back_btn:
            st.session_state.intro_done=False; st.rerun()
        if reg_btn:
            if not all([reg_fullname, reg_email, reg_username, reg_pw1, reg_pw2]):
                st.warning("⚠️ Please fill in all fields.")
            elif reg_pw1 != reg_pw2:
                st.error("❌ Passwords do not match.")
            elif len(reg_pw1) < 6:
                st.warning("⚠️ Password must be at least 6 characters.")
            else:
                ok, msg = _register_user(reg_username, reg_pw1, reg_fullname, reg_email)
                if ok:
                    st.success("✅ " + msg)
                    st.session_state.auth_mode="login"
                else:
                    st.error("❌ " + msg)

    st.markdown('<p style="text-align:center;color:#4B6080;font-size:12px;margin-top:20px;">© 2026 Chargevo — Secure Access</p>', unsafe_allow_html=True)


if not st.session_state.intro_done and not st.session_state.logged_in:
    intro_page()
    st.stop()

 
if not st.session_state.logged_in:
    login_page()
    st.stop()
 
if st.session_state.role == "Admin":
    try:
        init_database()
    except Exception as e:
        st.warning("Database initialization failed. Admin features may not work.")
 
 
# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────
# ── Header: logo left, title + role + logout right ──
h_col1, h_col2 = st.columns([1, 9])
with h_col1:
    try:
        st.image("logo_EV.jpeg", width=90)
    except Exception:
        st.markdown("""<div style="width:52px;height:52px;border-radius:14px;
            background:linear-gradient(135deg,#00E5B8,#38C8F8);display:flex;
            align-items:center;justify-content:center;font-size:26px;">⚡</div>""",
            unsafe_allow_html=True)
with h_col2:
    rc1, rc2 = st.columns([6, 1])
    with rc1:
        st.markdown(f"""
        <div style="padding-top:6px;">
          <div style="font-family:'Syne',sans-serif;font-size:26px;font-weight:800;
              color:white;letter-spacing:-0.03em;line-height:1.1;">
            Charge<span style="color:#00E5B8;">vo</span>
          </div>
          <div style="display:flex;align-items:center;gap:10px;margin-top:3px;">
            <div class="pill pill-teal" style="font-size:10px;padding:3px 10px;">⬤ Live</div>
            <div style="color:#8BA0BA;font-size:12px;">Role: <b style="color:white;">{st.session_state.role}</b></div>
            <div style="color:#4B6080;font-size:12px;">EV Charging Intelligence Platform</div>
          </div>
        </div>""", unsafe_allow_html=True)
    with rc2:
        if st.button("Logout", key="top_logout"):
            st.session_state.logged_in = False
            st.rerun()
st.markdown("</div>", unsafe_allow_html=True)
 
st.markdown("<div style='margin-bottom:0.5rem'></div>", unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────
# NAVIGATION  — one-click reliable native buttons
# ─────────────────────────────────────────
NAV_ITEMS_ADMIN = [
    ("Home", "🏠"), ("Prediction", "⚡"), ("Analytics", "📊"), ("Model", "🤖"),
    ("Admin Panel", "⚙️"), ("Book Slot", "📅"), ("About Us", "ℹ️"), ("Contact Us", "📞")
]
NAV_ITEMS_USER = [
    ("Home", "🏠"), ("Prediction", "⚡"), ("Book Slot", "📅"),
    ("About Us", "ℹ️"), ("Contact Us", "📞")
]

nav_items = NAV_ITEMS_ADMIN if st.session_state.role == "Admin" else NAV_ITEMS_USER
nav_options = [item[0] for item in nav_items]

if "page" not in st.session_state:
    st.session_state.page = "Home"
if "admin_page" not in st.session_state:
    st.session_state.admin_page = "Create EV Bunk"
if st.session_state.page not in nav_options:
    st.session_state.page = "Home"

st.markdown("""
<style>
.nav-shell{
    background:rgba(8,14,26,0.88);
    border:1px solid rgba(0,229,184,0.14);
    border-radius:20px;
    padding:10px 14px;
    box-shadow:0 4px 30px rgba(0,0,0,0.40);
    backdrop-filter:blur(20px);
    margin: 0.5rem 0 1.5rem;
}
.nav-shell div[data-testid="column"]{padding:0 4px !important;}
.nav-shell .stButton>button{
    height:48px !important;
    border-radius:14px !important;
    font-size:14px !important;
    font-weight:800 !important;
    box-shadow:none !important;
}
.nav-shell .stButton>button[kind="secondary"]{
    background:rgba(0,229,184,0.04) !important;
    border:1px solid transparent !important;
    color:#8BA0BA !important;
}
.nav-shell .stButton>button[kind="secondary"]:hover{
    background:rgba(0,229,184,0.11) !important;
    border-color:rgba(0,229,184,0.26) !important;
    color:#E8EEF6 !important;
}
/* admin-subnav-wrap removed — styles now applied inline via admin-subnav-row */
</style>
""", unsafe_allow_html=True)


nav_cols = st.columns(len(nav_items))
for col, (page_name, page_icon) in zip(nav_cols, nav_items):
    with col:
        btn_type = "primary" if st.session_state.page == page_name else "secondary"
        if st.button(f"{page_icon}  {page_name}", key=f"nav_{page_name}", use_container_width=True, type=btn_type):
            st.session_state.page = page_name
            st.rerun()


selected = st.session_state.page

admin_page = None
if selected == "Admin Panel" and st.session_state.role == "Admin":
    st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"]:has(button[kind="primary"][data-testid="baseButton-primary"]) + div { display: none !important; }
    .admin-subnav-row { margin: 0 0 1.2rem; }
    .admin-subnav-row .stButton>button[kind="primary"]{
        background:linear-gradient(135deg,#00E5B8,#38C8F8) !important;
        color:#04080F !important;
        border-radius:14px !important;
        height:48px !important;
        font-weight:800 !important;
        font-size:14px !important;
        box-shadow:0 4px 18px rgba(0,229,184,0.28) !important;
        border:none !important;
    }
    .admin-subnav-row .stButton>button[kind="secondary"]{
        background:rgba(0,229,184,0.05) !important;
        border:1px solid rgba(0,229,184,0.20) !important;
        color:#8BA0BA !important;
        border-radius:14px !important;
        height:48px !important;
        font-weight:700 !important;
        font-size:14px !important;
        box-shadow:none !important;
    }
    .admin-subnav-row .stButton>button[kind="secondary"]:hover{
        background:rgba(0,229,184,0.11) !important;
        color:#E8EEF6 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="admin-subnav-row">', unsafe_allow_html=True)
    a1, a2 = st.columns(2)
    with a1:
        if st.button("➕ Create EV Bunk", key="admin_create_nav", use_container_width=True,
                     type="primary" if st.session_state.admin_page == "Create EV Bunk" else "secondary"):
            st.session_state.admin_page = "Create EV Bunk"
            st.rerun()
    with a2:
        if st.button("🏢 Manage Bunk", key="admin_manage_nav", use_container_width=True,
                     type="primary" if st.session_state.admin_page == "Manage Bunk" else "secondary"):
            st.session_state.admin_page = "Manage Bunk"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    admin_page = st.session_state.admin_page

 
# ═══════════════════════════════════════════
#  HOME
# ═══════════════════════════════════════════
if selected == "Home":
    highest_state = df.groupby("state")["power_consumed"].sum().idxmax()
    lowest_state  = df.groupby("state")["power_consumed"].sum().idxmin()
    highest_value = df.groupby("state")["power_consumed"].sum().max()
    lowest_value  = df.groupby("state")["power_consumed"].sum().min()
    avg_demand    = df["power_consumed"].mean()
 
    # ── Hero
    st.markdown(f"""
    <div class="hero-wrap">
        <div class="hero-grid"></div>
        <div style="position:relative; z-index:1; display:flex; flex-direction:column; align-items:center;">
            <div class="hero-badge">⚡ AI-Powered Platform &nbsp;·&nbsp; <span style="color:var(--teal);">● System Active</span></div>
            <div class="hero-title">
                Smart EV Charging<br><span>Demand Intelligence</span>
            </div>
            <div class="hero-sub" style="text-align:center;">
                Predict charging demand, monitor station health, book EV charging slots,
                and plan infrastructure with real-time AI insights.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="hero-actions-wrap">', unsafe_allow_html=True)
    if st.session_state.role == "Admin":
        h_btn1, h_btn2 = st.columns(2)
        with h_btn1:
            if st.button("⚡ Demand Forecasting", key="hero_prediction_admin", use_container_width=True):
                st.session_state.page = "Prediction"
                st.rerun()
        with h_btn2:
            if st.button("📊 Analytics Dashboard", key="hero_analytics_admin", use_container_width=True):
                st.session_state.page = "Analytics"
                st.rerun()
    else:
        h_btn1, h_btn2 = st.columns(2)
        with h_btn1:
            if st.button("⚡ Demand Forecasting", key="hero_prediction_user", use_container_width=True):
                st.session_state.page = "Prediction"
                st.rerun()
        with h_btn2:
            if st.button("📅 Book Charging Slot", key="hero_booking_user", use_container_width=True):
                st.session_state.page = "Book Slot"
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Ticker
    st.markdown("""
    <div class="ticker-wrap">
        <div class="ticker-inner">
            ⚡ EV charging demand rising across metro cities
            <span class="sep">|</span>
            🚗 Four-wheelers require higher capacity fast chargers
            <span class="sep">|</span>
            🔧 Proactive maintenance reduces station downtime by 40%
            <span class="sep">|</span>
            📊 AI prediction improves infrastructure ROI
            <span class="sep">|</span>
            🌱 Smart charging supports India's net-zero goals
            <span class="sep">|</span>
            ⚡ Fast charging stations consume 3× more electricity
        </div>
    </div>
    """, unsafe_allow_html=True)
 
    # ── Top stats row
    s1, s2, s3, s4 = st.columns(4)
    stats = [
        ("🗂", f"{len(df):,}",             "Total Records"),
        ("🗺",  str(df["state"].nunique()), "States Covered"),
        ("🏙",  str(df["City"].nunique()),  "Cities Covered"),
        ("⚡",  f"{avg_demand:.1f} kW",    "Avg. Demand"),
    ]
    for col, (icon, number, label) in zip([s1,s2,s3,s4], stats):
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <span class="icon">{icon}</span>
                <div class="number">{number}</div>
                <div class="label">{label}</div>
                <div class="stripe"></div>
            </div>""", unsafe_allow_html=True)
 
    st.markdown("<div style='margin:1.5rem 0'></div>", unsafe_allow_html=True)
 
    # ── Demand highlights
    d1, d2 = st.columns(2)
    with d1:
        st.markdown(f"""
        <div class="demand-card demand-card-high">
            <h3>🔺 Highest Demand State</h3>
            <div class="d-state">{highest_state}</div>
            <div class="d-val">{highest_value:,.2f} kWh consumed</div>
        </div>""", unsafe_allow_html=True)
    with d2:
        st.markdown(f"""
        <div class="demand-card demand-card-low">
            <h3>🔻 Lowest Demand State</h3>
            <div class="d-state">{lowest_state}</div>
            <div class="d-val">{lowest_value:,.2f} kWh consumed</div>
        </div>""", unsafe_allow_html=True)
 
    st.markdown("<div style='margin:1.5rem 0'></div>", unsafe_allow_html=True)
 
    # ── Demand slider
    st.markdown('<div class="section-label">⚙ Charging Demand Indicator</div>', unsafe_allow_html=True)
    st.slider("Average EV Charging Demand (kW)", min_value=0, max_value=500,
              value=int(avg_demand), disabled=True)
    if avg_demand > 250:
        st.error("⚠️ EV charging demand is high. Infrastructure expansion recommended.")
    else:
        st.success("✅ Charging demand is within manageable limits.")
 
    # ── About
    st.markdown("<div style='margin:2rem 0 1rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">About this system</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="g-card">
        <div style="font-family:'Syne',sans-serif; font-size:22px; font-weight:700;
            color:white; margin-bottom:12px;">
            🚀 What is Chargevo?
        </div>
        <div style="color:#8BA0BA; font-size:15px; line-height:1.9;">
            Chargevo is an AI-powered EV Charging Demand Prediction System that helps users and 
            station operators understand real-time demand, estimate charging time &amp; cost, 
            monitor machine health, book slots, and plan infrastructure with confidence.
        </div>
    </div>""", unsafe_allow_html=True)
 
 
# ═══════════════════════════════════════════
#  PREDICTION
# ═══════════════════════════════════════════
if selected == "Prediction":
    st.markdown("""
    <div class="page-title-wrap">
        <div class="page-title">⚡ Demand Prediction</div>
        <div class="page-sub">Enter station parameters to forecast EV charging demand using AI</div>
    </div>""", unsafe_allow_html=True)
 
    # ── Location
    st.markdown('<div class="section-label">📍 Location</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        state = st.selectbox("Select State", sorted(df["state"].dropna().unique()))
    with col2:
        cities = sorted(df[df["state"] == state]["City"].dropna().unique())
        city   = st.selectbox("Select City", cities)
 
    st.markdown("<div style='margin:0.6rem 0'></div>", unsafe_allow_html=True)
    vehicle_type = st.selectbox("🚗 Vehicle Type",
        ["Two Wheeler","Three Wheeler","Four Wheeler","Goods Vehicle","Public Service Vehicle"])
 
    # ── Station config
    st.markdown('<div class="section-label">🔌 Station Configuration</div>', unsafe_allow_html=True)
    col3, col4, col5 = st.columns(3)
    with col3: power           = st.number_input("Power (kW)",         min_value=1.0,   value=50.0)
    with col4: total_machines  = st.number_input("Total Machines",     min_value=1,     value=10)
    with col5: damaged_machines= st.number_input("Damaged Machines",   min_value=0,     max_value=total_machines, value=1)
 
    working_machines = total_machines - damaged_machines
    damage_pct       = (damaged_machines / total_machines) * 100
 
    if   damaged_machines == 0:  condition, badge_cls = "Excellent", "badge-excellent"
    elif damage_pct <= 20:       condition, badge_cls = "Good",      "badge-good"
    elif damage_pct <= 40:       condition, badge_cls = "Moderate",  "badge-moderate"
    elif damage_pct <= 70:       condition, badge_cls = "Poor",      "badge-poor"
    else:                        condition, badge_cls = "Critical",  "badge-critical"
 
    # Machine status
    st.markdown(f"""
    <div class="g-card" style="margin:1rem 0;">
        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:16px;">
            <div><div class="section-label">Machine Health</div>
                <div style="font-family:'Syne',sans-serif; font-size:22px; font-weight:700; color:white; margin-top:4px;">
                    Station Status Overview
                </div>
            </div>
            <div class="machine-badge {badge_cls}">{condition}</div>
        </div>
        <div style="display:flex; gap:30px; margin-top:20px; flex-wrap:wrap;">
            <div><div style="color:#8BA0BA;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Total</div>
                <div style="font-family:'Syne',sans-serif;font-size:28px;font-weight:800;color:white;">{total_machines}</div></div>
            <div><div style="color:#8BA0BA;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Working</div>
                <div style="font-family:'Syne',sans-serif;font-size:28px;font-weight:800;color:#00E5B8;">{working_machines}</div></div>
            <div><div style="color:#8BA0BA;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Damaged</div>
                <div style="font-family:'Syne',sans-serif;font-size:28px;font-weight:800;color:#FF4B6B;">{damaged_machines}</div></div>
            <div><div style="color:#8BA0BA;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Damage %</div>
                <div style="font-family:'Syne',sans-serif;font-size:28px;font-weight:800;color:#F59E0B;">{damage_pct:.1f}%</div></div>
        </div>
    </div>""", unsafe_allow_html=True)
 
    if   condition == "Excellent": st.success("✅ All charging machines are operating perfectly.")
    elif condition == "Good":      st.info("ℹ️ Most machines running efficiently.")
    elif condition == "Moderate":  st.warning("⚠️ Some machines require maintenance.")
    elif condition == "Poor":      st.error("❌ Many machines are damaged. Maintenance required.")
    else:                          st.error("🚨 Critical condition. Service may be severely affected.")
 
    # ── Electrical parameters
    st.markdown('<div class="section-label">⚡ Electrical Parameters</div>', unsafe_allow_html=True)
    col6, col7, col8 = st.columns(3)
    with col6: voltage       = st.number_input("Voltage Level (V)",  min_value=1.0,  value=440.0)
    with col7: current       = st.number_input("Current Flow (A)",   min_value=1.0,  value=100.0)
    with col8: charging_type = st.selectbox("Charging Type",         list(encoder.classes_))
 
    # ── Vehicle details
    battery_capacity = {"Two Wheeler":3,"Three Wheeler":8,"Four Wheeler":40,"Goods Vehicle":80,"Public Service Vehicle":120}
    price_per_kwh    = {"Two Wheeler":8,"Three Wheeler":10,"Four Wheeler":15,"Goods Vehicle":18,"Public Service Vehicle":20}
    sel_bat  = battery_capacity[vehicle_type]
    sel_price= price_per_kwh[vehicle_type]
    est_time = sel_bat / power
    est_cost = sel_bat * sel_price
 
    st.markdown(f"""
    <div class="g-card" style="margin:1rem 0;">
        <div class="section-label">🚗 Vehicle Charging Estimate</div>
        <div style="display:flex; gap:30px; margin-top:14px; flex-wrap:wrap;">
            <div><div style="color:#8BA0BA;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Vehicle</div>
                <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:700;color:white;">{vehicle_type}</div></div>
            <div><div style="color:#8BA0BA;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Battery</div>
                <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:700;color:white;">{sel_bat} kWh</div></div>
            <div><div style="color:#8BA0BA;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Est. Time</div>
                <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:700;color:#38C8F8;">{est_time:.2f} hrs</div></div>
            <div><div style="color:#8BA0BA;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Est. Price</div>
                <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:700;color:#00E5B8;">₹{est_cost:.2f}</div></div>
        </div>
    </div>""", unsafe_allow_html=True)
 
    charging_type_encoded = encoder.transform([charging_type])[0]
 
    st.markdown("<div style='margin:0.8rem 0'></div>", unsafe_allow_html=True)
    if st.button("⚡  Run Demand Prediction", key="predict_demand_btn"):
        input_data = pd.DataFrame([[power, total_machines, voltage, current, charging_type_encoded]], columns=features)
        prediction = model.predict(input_data)[0]
 
        if   prediction < 100:  level, rec, col_accent = "Low Demand",    "Charging capacity is sufficient.",                  "#00E5B8"
        elif prediction < 250:  level, rec, col_accent = "Medium Demand", "Monitor station usage regularly.",                  "#F59E0B"
        else:                   level, rec, col_accent = "High Demand",   "High load detected — consider adding chargers.",    "#FF4B6B"
 
        st.markdown(f"""
        <div class="pred-result-wrap">
            <div class="section-label">Prediction Result</div>
            <div style="font-family:'Syne',sans-serif; font-size:52px; font-weight:800;
                color:{col_accent}; line-height:1; margin:10px 0 4px;">
                {prediction:.1f} kW
            </div>
            <div style="font-size:16px; color:#8BA0BA;">{level} — {rec}</div>
            <div style="margin-top:14px;">
                <span class="pill" style="background:rgba(255,255,255,0.05);
                    color:white; border:1px solid rgba(255,255,255,0.10);">
                    📍 {city}, {state}
                </span>
            </div>
        </div>""", unsafe_allow_html=True)
 
        if   level == "Low Demand":    st.success(f"✅ {rec}")
        elif level == "Medium Demand": st.warning(f"⚠️ {rec}")
        else:                          st.error(f"❌ {rec}")
 
        # Gauge
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=prediction,
            title={"text": "EV Demand Gauge (kW)", "font": {"color":"#8BA0BA","size":14}},
            number={"font":{"color":"white","size":40},"suffix":" kW"},
            gauge={
                "axis": {"range":[0,500],"tickcolor":"#8BA0BA","tickfont":{"color":"#8BA0BA"}},
                "bar":  {"color": col_accent, "thickness":0.25},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range":[0,100],   "color":"rgba(0,229,184,0.10)"},
                    {"range":[100,250], "color":"rgba(245,158,11,0.10)"},
                    {"range":[250,500], "color":"rgba(255,75,107,0.10)"},
                ],
                "threshold": {"line":{"color":col_accent,"width":3},"thickness":0.8,"value":prediction}
            }
        ))
        fig.update_layout(
            paper_bgcolor="rgba(8,14,26,0.80)",
            font={"color":"white"},
            height=320,
            margin=dict(l=30,r=30,t=50,b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
 
        # AI Insights
        st.markdown('<div class="section-label">🤖 AI Insights</div>', unsafe_allow_html=True)
        st.info(f"🚗 {vehicle_type} — estimated charge time: **{est_time:.2f} hrs**, cost: **₹{est_cost:.2f}**")
        if prediction > 250 and working_machines < 5:
            st.error("🚨 High demand + fewer working machines → expect long wait times.")
        if damage_pct > 50:
            st.error("❌ Over 50% machines are damaged. Urgent maintenance required.")
        if working_machines < 3:
            st.warning("⚠️ Very few working machines. Queue times will increase.")
        if vehicle_type in ["Goods Vehicle","Public Service Vehicle"]:
            st.warning("⚠️ Large vehicles need more power and longer charging duration.")
        if charging_type in ["Fast","Ultra Fast"]:
            st.info("ℹ️ Fast charging reduces time but increases station grid load.")
 
        # Download
        report = f"""
CHARGEVO — EV Charging Demand Prediction Report
================================================
State             : {state}
City              : {city}
Vehicle Type      : {vehicle_type}
Battery Capacity  : {sel_bat} kWh
Estimated Time    : {est_time:.2f} hours
Estimated Price   : ₹{est_cost:.2f}
 
Power             : {power} kW
Total Machines    : {total_machines}
Working Machines  : {working_machines}
Damaged Machines  : {damaged_machines}
Damage %          : {damage_pct:.2f}%
Machine Condition : {condition}
 
Voltage Level     : {voltage} V
Current Flow      : {current} A
Charging Type     : {charging_type}
 
Predicted Demand  : {prediction:.2f} kW
Demand Level      : {level}
Recommendation    : {rec}
================================================
© 2026 Chargevo — EV Charging Intelligence Platform
"""
        st.download_button("⬇ Download Prediction Report", data=report,
                           file_name="Chargevo_Demand_Report.txt", mime="text/plain")
 
 
# ═══════════════════════════════════════════
#  ANALYTICS  (Admin only)
# ═══════════════════════════════════════════
if st.session_state.role == "Admin" and selected == "Analytics":
    st.markdown("""
    <div class="page-title-wrap">
        <div class="page-title">📊 Analytics Dashboard</div>
        <div class="page-sub">Real-time EV charging demand insights across India</div>
    </div>""", unsafe_allow_html=True)
 
    highest_state = df.groupby("state")["power_consumed"].sum().idxmax()
    highest_city  = df.groupby("City")["power_consumed"].sum().idxmax()
    avg_demand    = df["power_consumed"].mean()
    max_demand    = df["power_consumed"].max()
 
    m1,m2,m3,m4 = st.columns(4)
    with m1: st.metric("Highest State",    highest_state)
    with m2: st.metric("Highest City",     highest_city)
    with m3: st.metric("Average Demand",   f"{avg_demand:.2f} kW")
    with m4: st.metric("Peak Demand",      f"{max_demand:.2f} kW")
 
    if avg_demand > 200:
        st.warning("⚠️ High overall demand. Expand charging infrastructure in peak states.")
    else:
        st.success("✅ Demand is manageable based on current data.")
 
    # ── Real-time interactive map using Folium + OpenStreetMap tiles
    st.markdown('<div class="section-label" style="margin-top:1.5rem;">🗺 EV Demand City Map — Real-Time Interactive</div>', unsafe_allow_html=True)

    city_coords = {
        "Delhi":(28.7041,77.1025), "Mumbai":(19.0760,72.8777),
        "Bangalore":(12.9716,77.5946), "Chennai":(13.0827,80.2707),
        "Kolkata":(22.5726,88.3639), "Hyderabad":(17.3850,78.4867),
        "Pune":(18.5204,73.8567), "Ahmedabad":(23.0225,72.5714),
        "Jaipur":(26.9124,75.7873), "Lucknow":(26.8467,80.9462),
        "Surat":(21.1702,72.8311), "Nagpur":(21.1458,79.0882),
        "Indore":(22.7196,75.8577), "Bhopal":(23.2599,77.4126),
        "Patna":(25.5941,85.1376), "Vadodara":(22.3072,73.1812),
        "Chandigarh":(30.7333,76.7794), "Coimbatore":(11.0168,76.9558),
        "Kochi":(9.9312,76.2673), "Visakhapatnam":(17.6868,83.2185),
        "Agra":(27.1767,78.0081), "Nashik":(19.9975,73.7898),
        "Meerut":(28.9845,77.7064), "Rajkot":(22.3039,70.8022),
        "Varanasi":(25.3176,82.9739), "Amritsar":(31.6340,74.8723),
        "Thiruvananthapuram":(8.5241,76.9366), "Guwahati":(26.1445,91.7362),
        "Bhubaneswar":(20.2961,85.8245), "Ranchi":(23.3441,85.3096),
        "Mysuru":(12.2958,76.6394), "Jabalpur":(23.1815,79.9864),
        "Port Blair":(11.6234,92.7265), "Shimla":(31.1048,77.1734),
        "Dehradun":(30.3165,78.0322), "Goa":(15.2993,74.1240),
        "Imphal":(24.8170,93.9368), "Aizawl":(23.7271,92.7176),
        "Gangtok":(27.3389,88.6065), "Itanagar":(27.0844,93.6053),
    }

    city_map_data = (
        df.groupby(["City","state"])["power_consumed"]
        .sum().reset_index()
        .rename(columns={"City":"city","state":"state","power_consumed":"demand"})
    )
    city_map_data["lat"] = city_map_data["city"].map(lambda c: city_coords.get(c,(None,None))[0])
    city_map_data["lon"] = city_map_data["city"].map(lambda c: city_coords.get(c,(None,None))[1])
    city_map_data = city_map_data.dropna(subset=["lat","lon"])
    max_demand = city_map_data["demand"].max()

    def demand_color(demand):
        ratio = demand / max_demand
        if ratio > 0.75:   return "#FF4B6B"
        elif ratio > 0.50: return "#F97316"
        elif ratio > 0.25: return "#F59E0B"
        else:              return "#00E5B8"

    def demand_label(demand):
        ratio = demand / max_demand
        if ratio > 0.75:   return "🔴 Critical"
        elif ratio > 0.50: return "🟠 High"
        elif ratio > 0.25: return "🟡 Medium"
        else:              return "🟢 Low"

    m = folium.Map(
        location=[22.5, 82.0],
        zoom_start=5,
        tiles=None,
        prefer_canvas=True,
    )
    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr="© OpenStreetMap contributors",
        name="OpenStreetMap",
        max_zoom=18,
    ).add_to(m)

    # Add legend as HTML
    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:9999;
        background:rgba(8,14,26,0.92);border:1px solid rgba(0,229,184,0.25);
        border-radius:14px;padding:14px 18px;font-family:DM Sans,sans-serif;">
      <div style="color:#00E5B8;font-size:12px;font-weight:700;letter-spacing:0.1em;
          text-transform:uppercase;margin-bottom:10px;">⚡ EV Demand Level</div>
      <div style="display:flex;flex-direction:column;gap:7px;">
        <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;
            background:#00E5B8;margin-right:8px;"></span><span style="color:#ccc;font-size:13px;">Low Demand</span></div>
        <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;
            background:#F59E0B;margin-right:8px;"></span><span style="color:#ccc;font-size:13px;">Medium Demand</span></div>
        <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;
            background:#F97316;margin-right:8px;"></span><span style="color:#ccc;font-size:13px;">High Demand</span></div>
        <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;
            background:#FF4B6B;margin-right:8px;"></span><span style="color:#ccc;font-size:13px;">Critical Demand</span></div>
      </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    for _, row in city_map_data.iterrows():
        color  = demand_color(row["demand"])
        radius = max(8, min(40, row["demand"] / max_demand * 40))
        label  = demand_label(row["demand"])

        popup_html = f"""
        <div style="font-family:DM Sans,sans-serif;min-width:200px;padding:4px;">
          <div style="font-size:16px;font-weight:700;color:#00E5B8;margin-bottom:6px;">
            ⚡ {row['city']}
          </div>
          <div style="color:#555;font-size:13px;margin-bottom:4px;">
            📍 {row['state']}
          </div>
          <hr style="border:none;border-top:1px solid #eee;margin:8px 0;">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
            <span style="color:#777;font-size:12px;">Total Demand</span>
            <span style="color:#111;font-weight:700;font-size:13px;">{row['demand']:,.0f} kWh</span>
          </div>
          <div style="display:flex;justify-content:space-between;">
            <span style="color:#777;font-size:12px;">Status</span>
            <span style="font-weight:700;font-size:13px;">{label}</span>
          </div>
        </div>
        """

        # Outer glow ring
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=radius + 6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.15,
            weight=0,
        ).add_to(m)

        # Main bubble
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.80,
            weight=2,
            popup=folium.Popup(popup_html, max_width=240),
            tooltip=folium.Tooltip(
                f"<b style='color:{color};'>{row['city']}</b><br>"
                f"<span style='font-size:12px;'>{row['demand']:,.0f} kWh · {label}</span>",
                sticky=True
            ),
        ).add_to(m)

    st_folium(m, width="100%", height=560, returned_objects=[])
 
    # Charts
    def styled_fig(fig):
        fig.update_layout(
            paper_bgcolor="rgba(8,14,26,0.80)",
            plot_bgcolor ="rgba(8,14,26,0.80)",
            font=dict(color="#8BA0BA", family="DM Sans"),
            title_font=dict(color="white", family="Syne", size=18),
            margin=dict(l=20,r=20,t=50,b=20),
        )
        fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="#8BA0BA"))
        fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="#8BA0BA"))
        return fig
 
    state_demand = df.groupby("state")["power_consumed"].sum().sort_values(ascending=False).head(10).reset_index()
    fig1 = px.bar(state_demand, x="state", y="power_consumed",
                  title="Top 10 States by Charging Demand",
                  color_discrete_sequence=["#00E5B8"])
    st.plotly_chart(styled_fig(fig1), use_container_width=True)
 
    city_demand = df.groupby("City")["power_consumed"].sum().sort_values(ascending=False).head(10).reset_index()
    fig2 = px.bar(city_demand, x="City", y="power_consumed",
                  title="Top 10 Cities by Charging Demand",
                  color_discrete_sequence=["#38C8F8"])
    st.plotly_chart(styled_fig(fig2), use_container_width=True)
 
    c_left, c_right = st.columns(2)
    with c_left:
        fig3 = px.pie(df, names="charging_type", title="Charging Type Distribution",
                      color_discrete_sequence=["#00E5B8","#38C8F8","#F97316","#8B5CF6"])
        fig3.update_traces(textfont_color="white")
        st.plotly_chart(styled_fig(fig3), use_container_width=True)
    with c_right:
        fig4 = px.histogram(df, x="power_consumed", nbins=30,
                            title="Power Consumption Distribution",
                            color_discrete_sequence=["#00E5B8"])
        st.plotly_chart(styled_fig(fig4), use_container_width=True)
 
    fig5 = px.scatter(df, x="num_chargers", y="power_consumed", color="charging_type",
                      title="Charger Count vs Power Consumed",
                      color_discrete_sequence=["#00E5B8","#38C8F8","#F97316","#8B5CF6"])
    st.plotly_chart(styled_fig(fig5), use_container_width=True)
 
 
# ═══════════════════════════════════════════
#  MODEL  (Admin only)
# ═══════════════════════════════════════════
if st.session_state.role == "Admin" and selected == "Model":
    st.markdown("""
    <div class="page-title-wrap">
        <div class="page-title">🤖 Model Performance</div>
        <div class="page-sub">ML model comparison and feature importance analysis</div>
    </div>""", unsafe_allow_html=True)
 
    def styled_fig(fig):
        fig.update_layout(
            paper_bgcolor="rgba(8,14,26,0.80)", plot_bgcolor="rgba(8,14,26,0.80)",
            font=dict(color="#8BA0BA", family="DM Sans"),
            title_font=dict(color="white", family="Syne", size=18),
            margin=dict(l=20,r=20,t=50,b=20)
        )
        fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
        fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
        return fig
 
    st.markdown('<div class="section-label">Model Comparison</div>', unsafe_allow_html=True)
    st.dataframe(model_results, use_container_width=True)
    fig6 = px.bar(model_results, x="Model", y="R2 Score", title="R² Score Comparison",
                  color_discrete_sequence=["#00E5B8"])
    st.plotly_chart(styled_fig(fig6), use_container_width=True)
 
    st.markdown('<div class="section-label">Feature Importance</div>', unsafe_allow_html=True)
    st.dataframe(feature_importance, use_container_width=True)
    fig7 = px.bar(feature_importance, x="Importance", y="Feature", orientation="h",
                  title="Feature Importance for EV Demand Prediction",
                  color_discrete_sequence=["#38C8F8"])
    st.plotly_chart(styled_fig(fig7), use_container_width=True)
 
 
# ═══════════════════════════════════════════
#  ADMIN — CREATE EV BUNK
# ═══════════════════════════════════════════
if selected == "Admin Panel" and admin_page == "Create EV Bunk":
    st.markdown("""
    <div class="page-title-wrap">
        <div class="page-title">➕ Create EV Bunk</div>
        <div class="page-sub">Register a new EV charging station in the network</div>
    </div>""", unsafe_allow_html=True)
 
    try:
        existing_bunks = read_sql_df("SELECT bunk_name FROM ev_bunks ORDER BY bunk_name")
        bunk_list = existing_bunks["bunk_name"].dropna().unique().tolist()
    except Exception:
        bunk_list = []
    bunk_list.append("➕ Add New EV Bunk")
 
    # Location selectors OUTSIDE form so city list reacts immediately when state changes
    st.markdown('<div class="section-label">📍 Location</div>', unsafe_allow_html=True)
    _loc1, _loc2 = st.columns(2)
    with _loc1:
        cb_state = st.selectbox("State", sorted(df["state"].dropna().unique()), key="cb_state")
    with _loc2:
        cb_city_opts = sorted(df[df["state"] == cb_state]["City"].dropna().unique())
        cb_city = st.selectbox("City", cb_city_opts, key="cb_city")

    with st.form("create_bunk_form"):
        selected_bunk = st.selectbox("Select or Add EV Bunk", bunk_list)
        bunk_name = st.text_input("EV Bunk Name", placeholder="Enter station name") if selected_bunk == "➕ Add New EV Bunk" else selected_bunk
        owner_name    = st.text_input("Owner Name",     placeholder="Full name")
        st.markdown(f"""<div style="padding:10px 14px; background:rgba(12,20,36,0.9); border:1px solid rgba(0,229,184,0.18);
            border-radius:12px; color:#8BA0BA; font-size:14px; margin-bottom:8px;">
            📍 Selected: &nbsp;<b style="color:#00E5B8;">{cb_state}</b> &nbsp;›&nbsp;
            <b style="color:#E8EEF6;">{cb_city}</b>
            &nbsp;&nbsp;<span style="font-size:11px; opacity:0.6;">(adjust the State / City dropdowns above ↑)</span>
        </div>""", unsafe_allow_html=True)
        address       = st.text_area("Address",         placeholder="Full address")
        c1,c2,c3      = st.columns(3)
        with c1: total_machines  = st.number_input("Total Machines", min_value=1, value=10)
        with c2: fast_chargers   = st.number_input("Fast Chargers",  min_value=0, value=3)
        with c3: normal_chargers = st.number_input("Normal Chargers",min_value=0, value=7)
        contact       = st.text_input("Contact Number", placeholder="+91 XXXXX XXXXX")
        submit_bunk   = st.form_submit_button("💾  Save EV Bunk", use_container_width=True)

        if submit_bunk:
            if not bunk_name.strip():
                st.error("Please enter a bunk name.")
            else:
                try:
                    execute_sql("""
                        INSERT INTO ev_bunks
                        (bunk_name,owner_name,state,city,address,total_machines,fast_chargers,normal_chargers,damaged_machines,working_machines,contact)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(bunk_name) DO UPDATE SET
                            owner_name=excluded.owner_name,
                            state=excluded.state,
                            city=excluded.city,
                            address=excluded.address,
                            total_machines=excluded.total_machines,
                            fast_chargers=excluded.fast_chargers,
                            normal_chargers=excluded.normal_chargers,
                            damaged_machines=excluded.damaged_machines,
                            working_machines=excluded.working_machines,
                            contact=excluded.contact
                    """, (bunk_name,owner_name,cb_state,cb_city,address,total_machines,fast_chargers,normal_chargers,0,total_machines,contact))
                    st.success("✅ EV Bunk saved successfully!")
                except Exception as e:
                    st.error("Failed to save EV Bunk.")
                    st.write(e)
 
 
# ═══════════════════════════════════════════
#  ADMIN — MANAGE BUNK
# ═══════════════════════════════════════════
if selected == "Admin Panel" and admin_page == "Manage Bunk":
    st.markdown("""
    <div class="page-title-wrap">
        <div class="page-title">🏢 Manage EV Bunks</div>
        <div class="page-sub">View, update, and maintain station records</div>
    </div>""", unsafe_allow_html=True)
 
    try:
        bunk_data = read_sql_df("SELECT * FROM ev_bunks")
        if bunk_data.empty:
            st.warning("No EV bunks found. Please create one first.")
        else:
            st.markdown('<div class="section-label">All Registered Bunks</div>', unsafe_allow_html=True)
            st.dataframe(bunk_data, use_container_width=True)
 
            st.markdown('<div class="section-label" style="margin-top:1.5rem;">Update Bunk</div>', unsafe_allow_html=True)
            selected_bunk = st.selectbox("Select EV Bunk to Update", bunk_data["bunk_name"].unique())
            row = bunk_data[bunk_data["bunk_name"]==selected_bunk].iloc[0]
 
            owner_name = st.text_input("Owner Name", value=str(row["owner_name"]))
            state_opts = sorted(df["state"].dropna().unique())
            state      = st.selectbox("State", state_opts,
                            index=state_opts.index(row["state"]) if row["state"] in state_opts else 0)
            city_opts  = sorted(df[df["state"]==state]["City"].dropna().unique())
            city       = st.selectbox("City", city_opts,
                            index=city_opts.index(row["city"]) if row["city"] in city_opts else 0)
            address    = st.text_area("Address",  value=str(row["address"]))
            contact    = st.text_input("Contact", value=str(row["contact"]))
 
            st.markdown('<div class="section-label" style="margin-top:1rem;">Machine Status</div>', unsafe_allow_html=True)
            mb1,mb2,mb3 = st.columns(3)
            with mb1: total_machines   = st.number_input("Total",   min_value=1, value=int(row["total_machines"]))
            with mb2: fast_chargers    = st.number_input("Fast",    min_value=0, value=int(row["fast_chargers"]))
            with mb3: normal_chargers  = st.number_input("Normal",  min_value=0, value=int(row["normal_chargers"]))
            damaged_machines = st.number_input("Damaged", min_value=0, max_value=total_machines, value=int(row["damaged_machines"]))
            working_machines = total_machines - damaged_machines
            st.metric("Working Machines", working_machines)
 
            if st.button("🔄 Update Bunk Details", key="update_bunk_btn"):
                execute_sql("""
                    UPDATE ev_bunks SET owner_name=?,state=?,city=?,address=?,contact=?,
                    total_machines=?,fast_chargers=?,normal_chargers=?,
                    damaged_machines=?,working_machines=? WHERE bunk_name=?
                """, (owner_name,state,city,address,contact,total_machines,fast_chargers,normal_chargers,
                      damaged_machines,working_machines,selected_bunk))
                st.success("✅ Bunk details updated successfully!")
    except Exception as e:
        st.error("Something went wrong.")
        st.write(e)

 
 
# ═══════════════════════════════════════════
#  BOOK SLOT  (visible to all users)
# ═══════════════════════════════════════════
if selected == "Book Slot":
    st.markdown("""
    <div class="page-title-wrap">
        <div class="page-title">&#128197; Book EV Charging Slot</div>
        <div class="page-sub">Reserve your charging slot and pay advance — quick &amp; easy</div>
    </div>""", unsafe_allow_html=True)

    try:
        bunk_data = read_sql_df("SELECT bunk_name,state,city FROM ev_bunks ORDER BY bunk_name")
        if bunk_data.empty:
            st.markdown("""
            <div style="text-align:center; padding:60px 20px;">
              <div style="font-size:48px; margin-bottom:16px;">&#128267;</div>
              <div style="font-family:Syne,sans-serif; font-size:22px; font-weight:700; color:white; margin-bottom:8px;">No EV Bunks Available</div>
              <div style="color:#8BA0BA; font-size:15px;">Please ask an admin to register a charging station first.</div>
            </div>""", unsafe_allow_html=True)
        else:
            # ── Location filter
            st.markdown('<div class="section-label">&#128205; Select Location</div>', unsafe_allow_html=True)
            bs_col1, bs_col2, bs_col3 = st.columns(3)
            with bs_col1:
                bs_state = st.selectbox("State", sorted(bunk_data["state"].dropna().unique()), key="bs_state")
            with bs_col2:
                bs_city_opts = sorted(bunk_data[bunk_data["state"] == bs_state]["city"].dropna().unique())
                bs_city = st.selectbox("City", bs_city_opts, key="bs_city")
            with bs_col3:
                filt_bunks = bunk_data[(bunk_data["state"] == bs_state) & (bunk_data["city"] == bs_city)]
                bs_bunk = st.selectbox("EV Bunk", filt_bunks["bunk_name"].unique(), key="bs_bunk")

            st.markdown("<div style='margin:1rem 0'></div>", unsafe_allow_html=True)

            # ── Customer details
            st.markdown('<div class="section-label">&#128101; Customer Details</div>', unsafe_allow_html=True)
            bs_c1, bs_c2 = st.columns(2)
            with bs_c1:
                bs_customer_name = st.text_input("Full Name", placeholder="Your full name", key="bs_name")
            with bs_c2:
                bs_customer_phone = st.text_input("Phone Number", placeholder="+91 XXXXX XXXXX", key="bs_phone")

            bs_vehicle_type = st.selectbox("Vehicle Type",
                ["Two Wheeler", "Three Wheeler", "Four Wheeler", "Goods Vehicle", "Public Service Vehicle"],
                key="bs_vehicle")

            # ── Slot details
            st.markdown('<div class="section-label" style="margin-top:1rem;">&#128197; Slot Details</div>', unsafe_allow_html=True)
            bs_d1, bs_d2, bs_d3 = st.columns(3)
            with bs_d1: bs_slot_date = st.date_input("Date", key="bs_date")
            with bs_d2: bs_slot_time = st.time_input("Time", key="bs_time")
            with bs_d3: bs_charging_type = st.selectbox("Charging Type", ["Normal", "Fast"], key="bs_charge_type")

            # Price calc
            battery_capacity = {"Two Wheeler":3,"Three Wheeler":8,"Four Wheeler":40,"Goods Vehicle":80,"Public Service Vehicle":120}
            price_per_kwh    = {"Two Wheeler":8,"Three Wheeler":10,"Four Wheeler":15,"Goods Vehicle":18,"Public Service Vehicle":20}
            bs_est_price = battery_capacity[bs_vehicle_type] * price_per_kwh[bs_vehicle_type]
            bs_adv_amount = bs_est_price * 0.30

            # ── Payment summary card
            st.markdown(f"""
            <div class="g-card" style="margin:1.2rem 0;">
                <div class="section-label">&#128176; Payment Summary</div>
                <div style="display:flex; gap:40px; margin-top:14px; flex-wrap:wrap;">
                    <div>
                        <div style="color:#8BA0BA;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">Vehicle</div>
                        <div style="font-family:Syne,sans-serif;font-size:20px;font-weight:700;color:white;">{bs_vehicle_type}</div>
                    </div>
                    <div>
                        <div style="color:#8BA0BA;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">Total Estimate</div>
                        <div style="font-family:Syne,sans-serif;font-size:28px;font-weight:800;color:white;">&#8377;{bs_est_price:.2f}</div>
                    </div>
                    <div>
                        <div style="color:#8BA0BA;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">Advance (30%)</div>
                        <div style="font-family:Syne,sans-serif;font-size:28px;font-weight:800;color:#00E5B8;">&#8377;{bs_adv_amount:.2f}</div>
                    </div>
                    <div>
                        <div style="color:#8BA0BA;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">Remaining</div>
                        <div style="font-family:Syne,sans-serif;font-size:28px;font-weight:800;color:#38C8F8;">&#8377;{bs_est_price - bs_adv_amount:.2f}</div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

            # ── Payment method
            st.markdown('<div class="section-label">&#128179; Payment Method</div>', unsafe_allow_html=True)
            bs_payment_method = st.selectbox("Method", ["UPI QR Code", "Debit Card", "Credit Card"], key="bs_pay_method")

            if bs_payment_method == "UPI QR Code":
                st.info("&#128242; Scan the QR code below to pay advance.")
                upi_id = "chargevo@upi"
                qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=upi://pay?pa={upi_id}&pn=Chargevo&am={bs_adv_amount:.2f}&cu=INR"
                qr_c1, qr_c2, qr_c3 = st.columns([1,1,3])
                with qr_c1:
                    st.image(qr_url, width=180)
                with qr_c2:
                    st.markdown(f"""
                    <div style="padding:16px; background:rgba(0,229,184,0.06); border:1px solid rgba(0,229,184,0.18);
                        border-radius:14px; margin-top:8px;">
                        <div style="color:#8BA0BA;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">UPI ID</div>
                        <div style="color:white;font-size:15px;font-weight:600;margin-top:4px;">{upi_id}</div>
                        <div style="color:#8BA0BA;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin-top:10px;">Amount</div>
                        <div style="color:#00E5B8;font-size:20px;font-weight:800;margin-top:2px;">&#8377;{bs_adv_amount:.2f}</div>
                    </div>""", unsafe_allow_html=True)
                if st.button("&#9989; I Have Paid via UPI", key="bs_upi_paid"):
                    st.session_state.payment_status = "Paid"
                    st.success("UPI payment confirmed!")
            else:
                pc1, pc2 = st.columns(2)
                with pc1:
                    bs_card_num = st.text_input("Card Number", placeholder="16-digit number", key="bs_card_num")
                with pc2:
                    bs_card_name = st.text_input("Name on Card", placeholder="As on card", key="bs_card_name")
                pe1, pe2, pe3 = st.columns(3)
                with pe1: bs_expiry = st.text_input("Expiry (MM/YY)", key="bs_expiry")
                with pe2: bs_cvv    = st.text_input("CVV", type="password", key="bs_cvv")
                with pe3: st.markdown("<div style='padding-top:28px;color:#8BA0BA;font-size:12px;'>3 digits on back</div>", unsafe_allow_html=True)
                if bs_card_num and bs_expiry and bs_cvv:
                    st.session_state.payment_status = "Paid"
                    st.success("&#9989; Card verified.")
                else:
                    st.session_state.payment_status = "Pending"

            # Payment status badge
            is_paid = st.session_state.payment_status == "Paid"
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:10px; margin:12px 0 20px;">
                <span style="color:#8BA0BA; font-size:14px; font-weight:600;">Payment Status:</span>
                <span class="pill {'pill-teal' if is_paid else 'pill-red'}">
                    {'&#9989; Paid' if is_paid else '&#9203; Pending'}
                </span>
            </div>""", unsafe_allow_html=True)

            # ── Confirm booking button
            if st.button("&#128197;  Confirm My Booking", key="bs_confirm_btn", use_container_width=True):
                if not bs_customer_name or not bs_customer_phone:
                    st.warning("Please enter your name and phone number.")
                elif not is_paid:
                    st.warning("Please complete the advance payment first.")
                else:
                    try:
                        bs_slot_date_str = bs_slot_date.strftime("%Y-%m-%d")
                        bs_slot_time_str = bs_slot_time.strftime("%H:%M:%S")

                        existing_slot = read_sql_df(
                            "SELECT * FROM slot_bookings WHERE bunk_name=? AND slot_date=? AND slot_time=?",
                            (bs_bunk, bs_slot_date_str, bs_slot_time_str)
)
                        if not existing_slot.empty:
                            st.error("&#128683; This slot is already booked. Please choose a different time.")
                        else:
                            execute_sql("""
                                INSERT INTO slot_bookings
                                (bunk_name,customer_name,phone,vehicle_type,slot_date,slot_time,
                                 charging_type,estimated_price,advance_amount,payment_method,payment_status)
                                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                            """, (bs_bunk, bs_customer_name, bs_customer_phone, bs_vehicle_type,
                                  bs_slot_date_str, bs_slot_time_str, bs_charging_type,
                                  bs_est_price, bs_adv_amount, bs_payment_method,
                                  st.session_state.payment_status))
                            st.success(f"&#9989; Slot booked successfully at {bs_bunk}!")
                            st.markdown(f"""
                            <div class="g-card" style="margin-top:1rem;">
                                <div class="section-label">&#127972; Booking Confirmation</div>
                                <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:14px;">
                                    <div><div style="color:#8BA0BA;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">Station</div>
                                    <div style="color:white;font-size:16px;font-weight:600;margin-top:2px;">{bs_bunk}</div></div>
                                    <div><div style="color:#8BA0BA;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">Customer</div>
                                    <div style="color:white;font-size:16px;font-weight:600;margin-top:2px;">{bs_customer_name}</div></div>
                                    <div><div style="color:#8BA0BA;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">Date &amp; Time</div>
                                    <div style="color:#38C8F8;font-size:16px;font-weight:600;margin-top:2px;">{bs_slot_date} at {bs_slot_time}</div></div>
                                    <div><div style="color:#8BA0BA;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">Advance Paid</div>
                                    <div style="color:#00E5B8;font-size:16px;font-weight:600;margin-top:2px;">&#8377;{bs_adv_amount:.2f}</div></div>
                                </div>
                            </div>""", unsafe_allow_html=True)
                            st.session_state.payment_status = "Pending"
                    except Exception as e:
                        st.error("Booking failed. Please try again.")
                        st.write(e)

            # ── View bookings (admin sees all, user sees only their own if name filled)
            st.markdown('<div class="section-label" style="margin-top:2rem;">&#128203; Your Bookings</div>', unsafe_allow_html=True)
            try:
                if st.session_state.role == "Admin":
                    slot_data = read_sql_df("SELECT * FROM slot_bookings ORDER BY id DESC")
                else:
                    if bs_customer_name:
                        slot_data = read_sql_df(
                            "SELECT * FROM slot_bookings WHERE customer_name=? ORDER BY id DESC",
                            (bs_customer_name,)
                        )
                    else:
                        slot_data = pd.DataFrame()
                        st.info("Enter your name above to see your bookings.")

                if not slot_data.empty:
                    st.dataframe(slot_data, use_container_width=True)
                elif st.session_state.role == "Admin":
                    st.info("No bookings found yet.")
            except Exception as e:
                st.error("Could not load bookings.")
                st.write(e)

    except Exception as e:
        st.error("Could not connect to database.")
        st.write(e)

# ═══════════════════════════════════════════
#  ABOUT US
# ═══════════════════════════════════════════
if selected == "About Us":
    try:
        st.image("about_banner.png", use_container_width=True)
    except Exception:
        pass
 
    st.markdown("""
    <div style="text-align:center; margin:2.5rem 0 2rem;">
        <div class="section-label" style="justify-content:center; display:flex;">About the Project</div>
        <div class="page-title" style="font-size:48px; text-align:center;">⚡ Chargevo</div>
        <div class="page-sub" style="text-align:center; margin:10px auto 0; max-width:500px;">
            Smart EV Charging Demand Prediction System — built with AI & love
        </div>
    </div>""", unsafe_allow_html=True)
 
    st.markdown("""
    <div class="about-card">
        <div class="about-card-title">📌 Project Overview</div>
        <div class="about-card-text">
            Chargevo is an AI-powered EV Charging Demand Prediction System.
            It predicts EV charging demand, monitors machine condition, manages EV bunk details,
            supports slot booking with payment, and provides rich analytics for infrastructure planning.
        </div>
    </div>""", unsafe_allow_html=True)
 
    mc1, mc2 = st.columns(2)
    with mc1:
        st.markdown("""
        <div class="about-card">
            <div class="about-card-title">🎯 Mission</div>
            <div class="about-card-text">
                Reduce EV charging wait times, improve station efficiency,
                support smart energy usage, and help operators plan smarter infrastructure.
            </div>
        </div>""", unsafe_allow_html=True)
    with mc2:
        st.markdown("""
        <div class="about-card">
            <div class="about-card-title">🌍 Vision</div>
            <div class="about-card-text">
                Build a smart EV charging ecosystem where AI predicts demand,
                manages machines, and improves the charging experience for all.
            </div>
        </div>""", unsafe_allow_html=True)
 
    # Features
    st.markdown("""
    <div class="about-card">
        <div class="about-card-title">🚀 Key Features</div>
        <div class="about-card-text">
            ✅ AI-powered EV charging demand prediction<br>
            ✅ Admin panel with full EV bunk management<br>
            ✅ Slot booking with UPI &amp; card payment simulation<br>
            ✅ Machine health monitoring &amp; condition alerts<br>
            ✅ Interactive analytics dashboard &amp; visual reports<br>
            ✅ MySQL database for persistent data storage
        </div>
    </div>""", unsafe_allow_html=True)
 
    # Team
    st.markdown('<div class="section-label" style="margin-top:2rem;">👥 Our Team</div>', unsafe_allow_html=True)
    t1,t2,t3,t4 = st.columns(4)
    team = [
        ("S","Soumili Ishat","Developer & ML Engineer","Streamlit app, ML model integration, MySQL, dashboard design & UI."),
        ("P","Paromita Haldar","Data Analysis","Dataset analysis, EV demand insights, data preprocessing & documentation."),
        ("R","Rakhi Ghosh","Research & Testing","Project research, feature testing, validation & presentation support."),
        ("T","Tabasum Parvin","Documentation","Report writing, workflow explanation & project summary."),
    ]
    for col, (initial, name, role, desc) in zip([t1,t2,t3,t4], team):
        with col:
            st.markdown(f"""
            <div class="team-card">
                <div class="team-avatar">{initial}</div>
                <div class="team-name">{name}</div>
                <div class="team-role">{role}</div>
                <div class="team-desc">{desc}</div>
            </div>""", unsafe_allow_html=True)
 
    # Tech stack
    st.markdown('<div class="section-label" style="margin-top:2rem;">🛠 Technologies Used</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="tech-row">
        <div class="tech-chip">🐍 Python</div>
        <div class="tech-chip">🌐 Streamlit</div>
        <div class="tech-chip">🗄 MySQL</div>
        <div class="tech-chip">🤖 Scikit-learn</div>
        <div class="tech-chip">📊 Plotly</div>
        <div class="tech-chip">🗺 Folium</div>
        <div class="tech-chip">🐼 Pandas</div>
        <div class="tech-chip">🔢 NumPy</div>
    </div>""", unsafe_allow_html=True)
 
# ═══════════════════════════════════════════
#  CONTACT US
# ═══════════════════════════════════════════
if selected == "Contact Us":
    st.markdown("""
    <div class="page-title-wrap">
        <div class="page-title">📬 Contact Us</div>
        <div class="page-sub">Get in touch — we'd love to hear from you</div>
    </div>""", unsafe_allow_html=True)
 
    cc1, cc2 = st.columns([1,1])
    with cc1:
        st.markdown("""
        <div class="contact-card">
            <div class="section-label">Get In Touch</div>
            <div class="contact-item">
                <div class="contact-icon">📧</div>
                <div>
                    <div class="contact-label">Email</div>
                    <div class="contact-val">soumili@example.com</div>
                </div>
            </div>
            <div class="contact-item">
                <div class="contact-icon">📍</div>
                <div>
                    <div class="contact-label">Location</div>
                    <div class="contact-val">Kolkata, West Bengal, India</div>
                </div>
            </div>
            <div class="contact-item">
                <div class="contact-icon">☎️</div>
                <div>
                    <div class="contact-label">Phone</div>
                    <div class="contact-val">+91 98765 43210</div>
                </div>
            </div>
            <div class="contact-item">
                <div class="contact-icon">🕐</div>
                <div>
                    <div class="contact-label">Response Time</div>
                    <div class="contact-val">Within 24 hours</div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)
 
    with cc2:
        st.markdown('<div class="section-label">Send Feedback</div>', unsafe_allow_html=True)
        name    = st.text_input("Your Name",    placeholder="Full name")
        email   = st.text_input("Your Email",   placeholder="your@email.com")
        subject = st.text_input("Subject",      placeholder="Brief subject")
        message = st.text_area("Message",       placeholder="Write your message here…", height=140)
        if st.button("📩  Send Message", key="submit_feedback_btn"):
            if name and email and message:
                st.success("✅ Message sent successfully! We'll respond within 24 hours.")
            else:
                st.warning("Please fill in name, email, and message.")
        st.markdown('</div>', unsafe_allow_html=True)
 
 
# ═══════════════════════════════════════════
#  FOOTER  — pure HTML (no columns glitch)
# ═══════════════════════════════════════════
st.markdown("""
<div style="margin-top:4rem; background:linear-gradient(180deg,rgba(8,14,26,0.95) 0%,rgba(4,8,15,1) 100%); border:1px solid rgba(0,229,184,0.12); border-radius:24px; overflow:hidden; box-shadow:0 -4px 60px rgba(0,0,0,0.50);">
  <div style="height:3px; background:linear-gradient(90deg,transparent 0%,#00E5B8 30%,#38C8F8 60%,transparent 100%);"></div>
  <div style="display:grid; grid-template-columns:2fr 1fr 1fr 1.2fr; gap:40px; padding:48px 48px 40px;">
    <div>
      <div style="font-family:Syne,sans-serif; font-size:28px; font-weight:800; color:white; letter-spacing:-0.03em; margin-bottom:12px;">
        &#9889; Charge<span style="color:#00E5B8;">vo</span>
      </div>
      <div style="color:#8BA0BA; font-size:14px; line-height:1.8; max-width:220px; margin-bottom:20px;">
        Smart AI-powered EV charging demand prediction and infrastructure management platform.
      </div>
      <div style="display:inline-flex; align-items:center; gap:8px; padding:8px 16px; background:rgba(0,229,184,0.08); border:1px solid rgba(0,229,184,0.22); border-radius:999px;">
        <span style="width:8px;height:8px;border-radius:50%;background:#00E5B8;box-shadow:0 0 8px #00E5B8;display:inline-block;"></span>
        <span style="color:#00E5B8;font-size:12px;font-weight:700;letter-spacing:0.08em;">SYSTEM LIVE</span>
      </div>
    </div>
    <div>
      <div style="font-family:Syne,sans-serif; font-size:13px; font-weight:700; color:white; text-transform:uppercase; letter-spacing:0.10em; margin-bottom:18px; padding-bottom:10px; border-bottom:1px solid rgba(0,229,184,0.15);">Platform</div>
      <div style="color:#8BA0BA; font-size:14px; line-height:2.4;">
        &#127968; Home<br>&#9889; Prediction<br>&#128202; Analytics<br>&#129302; Model<br>&#9881;&#65039; Admin Panel
      </div>
    </div>
    <div>
      <div style="font-family:Syne,sans-serif; font-size:13px; font-weight:700; color:white; text-transform:uppercase; letter-spacing:0.10em; margin-bottom:18px; padding-bottom:10px; border-bottom:1px solid rgba(0,229,184,0.15);">Services</div>
      <div style="color:#8BA0BA; font-size:14px; line-height:2.4;">
        &#128302; Demand Prediction<br>&#128200; Station Analytics<br>&#127970; Bunk Management<br>&#128197; Slot Booking<br>&#128295; Machine Monitor
      </div>
    </div>
    <div>
      <div style="font-family:Syne,sans-serif; font-size:13px; font-weight:700; color:white; text-transform:uppercase; letter-spacing:0.10em; margin-bottom:18px; padding-bottom:10px; border-bottom:1px solid rgba(0,229,184,0.15);">Get in Touch</div>
      <div style="display:flex; flex-direction:column; gap:12px;">
        <div style="display:flex; align-items:center; gap:10px;">
          <div style="width:32px;height:32px;border-radius:8px;background:rgba(0,229,184,0.10);display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;">&#128231;</div>
          <span style="color:#8BA0BA;font-size:13px;">chargevo@gmail.com</span>
        </div>
        <div style="display:flex; align-items:center; gap:10px;">
          <div style="width:32px;height:32px;border-radius:8px;background:rgba(0,229,184,0.10);display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;">&#128222;</div>
          <span style="color:#8BA0BA;font-size:13px;">+91 98765 43210</span>
        </div>
        <div style="display:flex; align-items:center; gap:10px;">
          <div style="width:32px;height:32px;border-radius:8px;background:rgba(0,229,184,0.10);display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;">&#128205;</div>
          <span style="color:#8BA0BA;font-size:13px;">Kolkata, West Bengal, India</span>
        </div>
        <div style="display:flex; align-items:center; gap:10px;">
          <div style="width:32px;height:32px;border-radius:8px;background:rgba(0,229,184,0.10);display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;">&#128336;</div>
          <span style="color:#8BA0BA;font-size:13px;">Response within 24 hrs</span>
        </div>
      </div>
    </div>
  </div>
  <div style="height:1px; background:rgba(255,255,255,0.06); margin:0 48px;"></div>
  <div style="display:flex; align-items:center; justify-content:space-between; padding:20px 48px; flex-wrap:wrap; gap:12px;">
    <div style="color:#4B6080; font-size:13px;">
      &#169; 2026 <span style="color:#00E5B8; font-weight:600;">Chargevo</span> &#8212; EV Charging Intelligence Platform. All Rights Reserved.
    </div>
    <div style="display:flex; gap:8px;">
      <span style="padding:4px 12px; background:rgba(0,229,184,0.07); border:1px solid rgba(0,229,184,0.15); border-radius:999px; color:#8BA0BA; font-size:11px; font-weight:600;">Python</span>
      <span style="padding:4px 12px; background:rgba(56,200,248,0.07); border:1px solid rgba(56,200,248,0.15); border-radius:999px; color:#8BA0BA; font-size:11px; font-weight:600;">Streamlit</span>
      <span style="padding:4px 12px; background:rgba(0,229,184,0.07); border:1px solid rgba(0,229,184,0.15); border-radius:999px; color:#8BA0BA; font-size:11px; font-weight:600;">AI / ML</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)



# Floating chatbot is visible on every logged-in page for both User and Admin
render_floating_chatbot()
