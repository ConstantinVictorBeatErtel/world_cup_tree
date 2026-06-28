import streamlit as st
import streamlit.components.v1 as components
import requests
from bs4 import BeautifulSoup
import re
import json
import constants
import urllib.parse

# Page configuration
st.set_page_config(
    layout="wide",
    page_title="2026 FIFA World Cup Predictor",
    page_icon="⚽"
)

# Custom Dark CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global styles */
    .stApp {
        background-color: #0e0e12;
        color: #e8e8f0;
        font-family: 'Outfit', 'Inter', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #e8e8f0 !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 800 !important;
    }
    
    /* Section Title style */
    .section-title {
        font-size: 16px;
        font-weight: 800;
        color: #e8e8f0;
        border-left: 4px solid #f5c518;
        padding-left: 10px;
        margin-bottom: 16px;
        margin-top: 24px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Custom button overrides */
    .stButton>button {
        border-radius: 8px;
        background-color: #1e1e28;
        color: #e8e8f0;
        border: 1px solid #2a2a35;
        font-weight: 600;
        transition: all 0.15s;
    }
    .stButton>button:hover {
        border-color: #f5c518 !important;
        color: #f5c518 !important;
        background-color: #252530;
    }
    
    /* Dark style for stRadio container */
    div[data-testid="stRadio"] > div {
        background-color: #1a1a24;
        border-radius: 8px;
        padding: 4px;
        border: 1px solid #2a2a35;
    }
    
    /* Custom styles for stRadio labels */
    div[data-testid="stRadio"] label {
        color: #e8e8f0 !important;
    }
    
    /* Double-sided bracket CSS (Dark) */
    .bracket-scroll-container {
        overflow-x: auto;
        padding: 24px 16px;
        background-color: #0b0b0f;
        border: 1px solid #1f1f2e;
        border-radius: 12px;
        margin-top: 16px;
    }
    .bracket-flex-layout {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        min-width: 1480px;
        height: 820px;
    }
    .bracket-column {
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 145px;
        min-width: 135px;
        flex-shrink: 0;
        height: 100%;
    }
    .bracket-header {
        font-size: 9px;
        font-weight: 800;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 16px;
        text-align: center;
        border-bottom: 2px solid #2a2a35;
        width: 100%;
        padding-bottom: 8px;
    }
    .bracket-matches-flex {
        display: flex;
        flex-direction: column;
        justify-content: space-around;
        flex-grow: 1;
        width: 100%;
        height: calc(100% - 30px);
    }
    .bracket-card {
        background-color: #16161e;
        border: 1px solid #2a2a35;
        border-radius: 8px;
        padding: 6px;
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 11px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.12);
        transition: all 0.15s;
    }
    .bracket-card:hover {
        border-color: #f5c518;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .bracket-match-title {
        font-size: 8px;
        font-weight: 700;
        color: #6b7280;
        display: flex;
        justify-content: space-between;
        margin-bottom: 2px;
    }
    .bracket-team-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 4px 6px;
        border-radius: 4px;
        text-decoration: none !important;
        color: #e8e8f0 !important;
        background-color: transparent;
        border: 1px solid transparent;
        transition: all 0.1s ease-in-out;
        font-weight: 500;
    }
    .bracket-team-row.clickable {
        cursor: pointer;
    }
    .bracket-team-row.clickable:hover {
        background-color: #252530;
    }
    .bracket-team-row.active {
        background-color: rgba(34, 197, 94, 0.15) !important;
        border-color: #22c55e;
        font-weight: 700;
    }
    .bracket-team-row.active:hover {
        background-color: rgba(34, 197, 94, 0.22) !important;
    }
    .bracket-team-row.disabled {
        color: #6b7280 !important;
        cursor: not-allowed;
        opacity: 0.6;
    }
</style>
""", unsafe_allow_html=True)

# Helper to clean footnotes and parse integers
def clean_int(val):
    if not val:
        return 0
    # Strip footnotes like [a] or [1]
    val_cleaned = re.sub(r'\[\w+\]', '', val).strip()
    # Handle minus sign variations and positive signs
    val_cleaned = val_cleaned.replace("−", "-").replace("–", "-").replace("+", "")
    if not val_cleaned:
        return 0
    try:
        return int(val_cleaned)
    except ValueError:
        return 0

# Helper function to format team flag + name
def f(name):
    if not name:
        return "TBD"
    flag = constants.FLAG.get(name, "🏳️")
    return f"{flag} {name}"

# Format team for select pick widgets (inside st.radio)
def format_team(name):
    if name == "Draw":
        return "Draw"
    return f(name)

# Helper to format GD
def fmt_gd(n):
    return f"+{n}" if n > 0 else str(n)

# Live scraping function with fallback
@st.cache_data(ttl=60)  # Cache for 1 minute for live update responsiveness
def get_live_data():
    url = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    standings_data = {}
    match_results = []
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            tables = soup.find_all("table", class_="wikitable")
            
            # Scrape standings for settled groups A-F (tables 6 to 11)
            groups_A_F = ["A", "B", "C", "D", "E", "F"]
            table_indices = range(6, 12)
            
            for g_key, t_idx in zip(groups_A_F, table_indices):
                if t_idx < len(tables):
                    table = tables[t_idx]
                    rows = table.find_all("tr")
                    group_teams = []
                    
                    for row in rows:
                        cols = [td.get_text().strip() for td in row.find_all(["td", "th"])]
                        if not cols:
                            continue
                        rank_cleaned = re.sub(r'\[\w+\]', '', cols[0]).strip()
                        if len(cols) >= 10 and rank_cleaned.isdigit():
                            # Extract team name
                            team_cell = row.find_all(["td", "th"])[1]
                            team_link = team_cell.find("a")
                            team_name = team_link.get_text().strip() if team_link else cols[1]
                            
                            # Clean team name (remove parentheses and footnotes)
                            team_name = re.sub(r'\s*\([^)]*\)\s*', '', team_name)
                            team_name = re.sub(r'\[\w+\]', '', team_name)
                            team_name = team_name.strip()
                            
                            # Normalize
                            normalization_map = {
                                "Bosnia and Herzegovina": "Bosnia & Herz.",
                                "Czech Republic": "Czechia",
                                "Turkey": "Türkiye",
                                "DR Congo": "DR Congo",
                                "United States": "USA"
                            }
                            team_name = normalization_map.get(team_name, team_name)
                            
                            gf = clean_int(cols[6])
                            gd = clean_int(cols[8])
                            pts = clean_int(cols[9])
                            
                            group_teams.append({
                                "name": team_name,
                                "gf": gf,
                                "gd": gd,
                                "pts": pts
                            })
                            
                    if len(group_teams) == 4:
                        group_teams.sort(key=lambda x: (-x['pts'], -x['gd'], -x['gf']))
                        standings_data[g_key] = group_teams
            
            # Scrape match results for scores
            matches = soup.find_all("div", class_="footballbox")
            for m in matches:
                home = m.find("th", class_="fhome")
                away = m.find("th", class_="faway")
                score = m.find(["td", "th"], class_="fscore")
                
                home_name = home.get_text().strip() if home else ""
                away_name = away.get_text().strip() if away else ""
                score_text = score.get_text().strip() if score else ""
                
                if home_name and away_name:
                    home_name = re.sub(r'\s*\([^)]*\)\s*', '', home_name)
                    home_name = re.sub(r'\[\w+\]', '', home_name).strip()
                    
                    away_name = re.sub(r'\s*\([^)]*\)\s*', '', away_name)
                    away_name = re.sub(r'\[\w+\]', '', away_name).strip()
                    
                    normalization_map = {
                        "Bosnia and Herzegovina": "Bosnia & Herz.",
                        "Czech Republic": "Czechia",
                        "Turkey": "Türkiye",
                        "DR Congo": "DR Congo",
                        "United States": "USA"
                    }
                    home_name = normalization_map.get(home_name, home_name)
                    away_name = normalization_map.get(away_name, away_name)
                    
                    match_results.append({
                        "home": home_name,
                        "away": away_name,
                        "score": score_text
                    })
                    
    except Exception as e:
        st.warning(f"Live scraping temporarily unavailable. Using pre-loaded stats fallback. (Error: {e})")
        
    return standings_data, match_results

# Fetch live data
live_standings, live_matches = get_live_data()

# Helper to check if a match is finished in live data
def check_finished_match(home, away):
    for m in live_matches:
        if m['home'] == home and m['away'] == away:
            if re.search(r'\d+[–\-]\d+', m['score']):
                return True, m['score']
        elif m['home'] == away and m['away'] == home:
            if re.search(r'\d+[–\-]\d+', m['score']):
                nums = re.findall(r'\d+', m['score'])
                if len(nums) >= 2:
                    return True, f"{nums[1]}–{nums[0]}"
                return True, m['score']
    return False, "v"

# Handle local fallbacks for pre-settled groups A-F
fallback_standings = {}
for g in ["A", "B", "C", "D", "E", "F"]:
    fallback_standings[g] = [
        {"name": team["name"], "pts": team["pts"], "gd": team["gd"], "gf": team["gf"]}
        for team in constants.S_STANDINGS[g]
    ]

# Merge live standings for A-F
base_standings = {}
for g in ["A", "B", "C", "D", "E", "F"]:
    base_standings[g] = live_standings.get(g, fallback_standings[g])

# State Initialization
if 'picks' not in st.session_state:
    st.session_state.picks = {
        f"{g}_{i}": 'h' for g in ["G", "H", "I", "J", "K", "L"] for i in range(2)
    }

if 'bracket_picks' not in st.session_state:
    st.session_state.bracket_picks = {}

# Handle query parameters resets and picks.
#
# Clicking a team navigates the page, which on Streamlit Cloud starts a fresh
# session and wipes st.session_state. To survive that, every bracket link
# carries the COMPLETE state in the URL: gp = group (MD3) picks, bp = bracket
# picks. We rebuild session_state from those params on each load and leave them
# in the URL so subsequent reloads keep restoring the full state.
query_params = st.query_params

if "action" in query_params:
    action = query_params["action"]
    if action == "reset_groups":
        st.session_state.picks = {
            f"{g}_{i}": 'h' for g in ["G", "H", "I", "J", "K", "L"] for i in range(2)
        }
    elif action == "reset_bracket":
        st.session_state.bracket_picks = {}
    elif action == "reset_all":
        st.session_state.picks = {
            f"{g}_{i}": 'h' for g in ["G", "H", "I", "J", "K", "L"] for i in range(2)
        }
        st.session_state.bracket_picks = {}
    st.query_params.clear()
    st.rerun()

if "gp" in query_params:
    try:
        st.session_state.picks = json.loads(query_params["gp"])
    except (ValueError, TypeError):
        pass

if "bp" in query_params:
    try:
        st.session_state.bracket_picks = json.loads(query_params["bp"])
    except (ValueError, TypeError):
        pass

# ── HEADER ──
st.markdown("""
<div style="background-color: #101018; border-bottom: 1px solid #2a2a35; padding: 20px 24px; margin: -6em -4em 2em -4em; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
    <div>
        <div style="font-size: 11px; letter-spacing: 0.15em; color: #6b7280; text-transform: uppercase; font-weight: 700;">
            2026 FIFA World Cup
        </div>
        <h1 style="margin: 0; font-size: 26px; font-weight: 800; color: #e8e8f0; letter-spacing: -0.02em;">
            ⚽ R32 & Knockout Bracket Predictor
        </h1>
        <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">
            Consolidated Unified Dashboard · Scrapes live standings & scores from Wikipedia dynamically!
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Quick actions row
col_status, col_btn1, col_btn2, col_btn3 = st.columns([3, 1, 1, 1])
with col_status:
    if st.button("🔄 Scrape Live Scores & Update Standings", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col_btn1:
    if st.button("Reset Matches", use_container_width=True):
        st.session_state.picks = {
            f"{g}_{i}": 'h' for g in ["G", "H", "I", "J", "K", "L"] for i in range(2)
        }
        st.rerun()
with col_btn2:
    if st.button("Reset Bracket", use_container_width=True):
        st.session_state.bracket_picks = {}
        st.rerun()
with col_btn3:
    if st.button("Reset All", use_container_width=True):
        st.session_state.picks = {
            f"{g}_{i}": 'h' for g in ["G", "H", "I", "J", "K", "L"] for i in range(2)
        }
        st.session_state.bracket_picks = {}
        st.rerun()

st.write("")

# ── ALL COMPUTATION ──

# Build a list of all fixtures G-L
md3_matches = []
pending_groups = ["G", "H", "I", "J", "K", "L"]
for gKey in pending_groups:
    matches_list = constants.GROUPS[gKey]["matches"]
    for i, (h, a) in enumerate(matches_list):
        finished, score = check_finished_match(h, a)
        md3_matches.append({
            "group": gKey,
            "index": i,
            "home": h,
            "away": a,
            "finished": finished,
            "score": score
        })

# Calculate live standings G-L mathematically from pre-MD3 base stats
standings = {}
for gKey in ["G", "H", "I", "J", "K", "L"]:
    base_teams = constants.GROUPS[gKey]["teams"]
    s = {
        name: {
            "name": name,
            "gf": info["gf"],
            "ga": info["ga"],
            "gd": info["gd"],
            "pts": info["pts"]
        }
        for name, info in base_teams.items()
    }
    
    # Process both MD3 matches
    matches_list = constants.GROUPS[gKey]["matches"]
    for i, (h, a) in enumerate(matches_list):
        finished, score = check_finished_match(h, a)
        
        if finished:
            # Parse score robustly (extracting all digit sequences)
            score_cleaned = score.replace("−", "-").replace("–", "-")
            nums = re.findall(r'\d+', score_cleaned)
            if len(nums) >= 2:
                gh = int(nums[0])
                ga = int(nums[1])
                
                # Apply stats
                s[h]["gf"] += gh
                s[h]["ga"] += ga
                s[h]["gd"] += (gh - ga)
                s[a]["gf"] += ga
                s[a]["ga"] += gh
                s[a]["gd"] += (ga - gh)
                
                if gh > ga:
                    s[h]["pts"] += 3
                elif ga > gh:
                    s[a]["pts"] += 3
                else:
                    s[h]["pts"] += 1
                    s[a]["pts"] += 1
        else:
            # Use user prediction
            r = st.session_state.picks.get(f"{gKey}_{i}", 'h')
            # Win/draw assumed as 1-0 or 0-0
            if r == 'h':
                s[h]["pts"] += 3
                s[h]["gf"] += 1
                s[h]["gd"] += 1
                s[a]["ga"] += 1
                s[a]["gd"] -= 1
            elif r == 'a':
                s[a]["pts"] += 3
                s[a]["gf"] += 1
                s[a]["gd"] += 1
                s[h]["ga"] += 1
                s[h]["gd"] -= 1
            else:
                s[h]["pts"] += 1
                s[a]["pts"] += 1
                # 0-0 draw assumed, no changes to gf, ga, gd
                
    teams_list = list(s.values())
    teams_list.sort(key=lambda x: (-x['pts'], -x['gd'], -x['gf']))
    standings[gKey] = teams_list

# Combine all standings A-L
all_group_standings = {}
for g in ["A", "B", "C", "D", "E", "F"]:
    all_group_standings[g] = base_standings[g]
for g in ["G", "H", "I", "J", "K", "L"]:
    all_group_standings[g] = standings[g]

# Calculate 3rd place standings
list_thirds = []
# Settled groups
for g in ["A", "B", "C", "D", "E", "F"]:
    t = all_group_standings[g][2] # index 2 is 3rd place
    list_thirds.append({
        "group": g,
        "name": t["name"],
        "pts": t["pts"],
        "gd": t["gd"],
        "gf": t["gf"],
        "settled": True
    })
# Live groups
for g in ["G", "H", "I", "J", "K", "L"]:
    t = standings[g][2]
    list_thirds.append({
        "group": g,
        "name": t["name"],
        "pts": t["pts"],
        "gd": t["gd"],
        "gf": t["gf"],
        "settled": False
    })
list_thirds.sort(key=lambda x: (-x['pts'], -x['gd'], -x['gf']))

# Add ranks and qualifies flags
all_thirds = []
for idx, t in enumerate(list_thirds):
    all_thirds.append({
        **t,
        "rank": idx + 1,
        "qualifies": idx < 8
    })

# Compute 3rd-place assign/get3 (needed for bracket)
qualGroups = "".join(sorted([t["group"] for t in all_thirds if t["qualifies"]]))
combo = constants.COMBOS.get(qualGroups, "")
assign = {}
if len(combo) == 8:
    for idx, sl in enumerate(constants.SLOT_ORDER):
        assign[sl] = combo[idx]
byGroup = {t["group"]: t["name"] for t in all_thirds}
def get3(sl):
    src = assign.get(sl)
    return byGroup.get(src, f"3rd Grp {src}" if src else "?")

group_keys = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]

# ── SECTION 1: Matches Grid ──
st.markdown('<div class="section-title">1. Decide Matchday 3 Fixtures</div>', unsafe_allow_html=True)

cols = st.columns(4)
for idx, match in enumerate(md3_matches):
    col_idx = idx % 4
    gKey = match["group"]
    i = match["index"]
    h = match["home"]
    a = match["away"]
    finished = match["finished"]
    score = match["score"]

    r = st.session_state.picks.get(f"{gKey}_{i}", 'h')

    with cols[col_idx]:
        with st.container(border=True):
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="color: #f5c518; font-weight: 800; font-size: 11px; letter-spacing: 0.05em;">GROUP {gKey}</span>
                <span style="font-size: 9px; color: #6b7280; font-weight: bold; background: #1e1e28; padding: 2px 6px; border-radius: 4px; border: 1px solid #2a2a35;">Fixture {i+1}</span>
            </div>
            """, unsafe_allow_html=True)

            if finished:
                st.markdown(f"""
                <div style="display: flex; flex-direction: column; gap: 8px; margin: 4px 0; text-align: center;">
                    <div style="font-size: 13px; font-weight: bold; color: #e8e8f0;">{f(h)}</div>
                    <div style="font-size: 16px; font-weight: 800; color: #0e0e12; background: #f5c518; padding: 4px; border-radius: 6px; width: 60px; margin: 0 auto; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.25));">{score}</div>
                    <div style="font-size: 13px; font-weight: bold; color: #e8e8f0;">{f(a)}</div>
                    <div style="font-size: 10px; color: #22c55e; font-weight: bold; margin-top: 4px;">✓ Live Results Sync</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="font-size: 12px; font-weight: bold; color: #e8e8f0; margin-bottom: 6px; text-align: center;">
                    {f(h).split(' ')[0]} vs {f(a).split(' ')[0]}
                </div>
                """, unsafe_allow_html=True)

                selected = st.radio(
                    label=f"select_{gKey}_{i}",
                    options=[h, "Draw", a],
                    index=0 if r == 'h' else (1 if r == 'd' else 2),
                    horizontal=True,
                    key=f"widget_{gKey}_{i}",
                    format_func=format_team,
                    label_visibility="collapsed"
                )
                if selected == h:
                    st.session_state.picks[f"{gKey}_{i}"] = 'h'
                elif selected == "Draw":
                    st.session_state.picks[f"{gKey}_{i}"] = 'd'
                else:
                    st.session_state.picks[f"{gKey}_{i}"] = 'a'

# ── SECTION 2: Knockout Bracket ──
st.markdown('<div class="section-title">2. Interactive Knockout Bracket</div>', unsafe_allow_html=True)
st.caption("Click on any team in the bracket matchups below to advance them to the next round!")

# R32 Teams setup
W = {g: all_group_standings[g][0]["name"] for g in group_keys}
R = {g: all_group_standings[g][1]["name"] for g in group_keys}

r32 = {
    'M73': { 't1': R['A'], 't2': R['B'], 'label': 'RU-A vs RU-B' },
    'M74': { 't1': W['E'], 't2': get3('E'), 'label': f"W-E vs 3rd-{assign.get('E', '?')}" },
    'M75': { 't1': W['F'], 't2': R['C'], 'label': 'W-F vs RU-C' },
    'M76': { 't1': W['C'], 't2': R['F'], 'label': 'W-C vs RU-F' },
    'M77': { 't1': W['I'], 't2': get3('I'), 'label': f"W-I vs 3rd-{assign.get('I', '?')}" },
    'M78': { 't1': R['E'], 't2': R['I'], 'label': 'RU-E vs RU-I' },
    'M79': { 't1': W['A'], 't2': get3('A'), 'label': f"W-A vs 3rd-{assign.get('A', '?')}" },
    'M80': { 't1': W['L'], 't2': get3('L'), 'label': f"W-L vs 3rd-{assign.get('L', '?')}" },
    'M81': { 't1': W['D'], 't2': get3('D'), 'label': f"W-D vs 3rd-{assign.get('D', '?')}" },
    'M82': { 't1': W['G'], 't2': get3('G'), 'label': f"W-G vs 3rd-{assign.get('G', '?')}" },
    'M83': { 't1': R['K'], 't2': R['L'], 'label': 'RU-K vs RU-L' },
    'M84': { 't1': W['H'], 't2': R['J'], 'label': 'W-H vs RU-J' },
    'M85': { 't1': W['B'], 't2': get3('B'), 'label': f"W-B vs 3rd-{assign.get('B', '?')}" },
    'M86': { 't1': W['J'], 't2': R['H'], 'label': 'W-J vs RU-H' },
    'M87': { 't1': W['K'], 't2': get3('K'), 'label': f"W-K vs 3rd-{assign.get('K', '?')}" },
    'M88': { 't1': R['D'], 't2': R['G'], 'label': 'RU-D vs RU-G' },
}

def getW(mid, t1, t2):
    picked = st.session_state.bracket_picks.get(mid)
    if picked and (picked == t1 or picked == t2):
        return picked
    return None

r16 = {
    'M89': { 't1': getW('M74', r32['M74']['t1'], r32['M74']['t2']), 't2': getW('M77', r32['M77']['t1'], r32['M77']['t2']), 'label': 'Winner M74 vs M77', 'p1': 'Winner M74', 'p2': 'Winner M77' },
    'M90': { 't1': getW('M73', r32['M73']['t1'], r32['M73']['t2']), 't2': getW('M75', r32['M75']['t1'], r32['M75']['t2']), 'label': 'Winner M73 vs M75', 'p1': 'Winner M73', 'p2': 'Winner M75' },
    'M91': { 't1': getW('M76', r32['M76']['t1'], r32['M76']['t2']), 't2': getW('M78', r32['M78']['t1'], r32['M78']['t2']), 'label': 'Winner M76 vs M78', 'p1': 'Winner M76', 'p2': 'Winner M78' },
    'M92': { 't1': getW('M79', r32['M79']['t1'], r32['M79']['t2']), 't2': getW('M80', r32['M80']['t1'], r32['M80']['t2']), 'label': 'Winner M79 vs M80', 'p1': 'Winner M79', 'p2': 'Winner M80' },
    'M93': { 't1': getW('M83', r32['M83']['t1'], r32['M83']['t2']), 't2': getW('M84', r32['M84']['t1'], r32['M84']['t2']), 'label': 'Winner M83 vs M84', 'p1': 'Winner M83', 'p2': 'Winner M84' },
    'M94': { 't1': getW('M81', r32['M81']['t1'], r32['M81']['t2']), 't2': getW('M82', r32['M82']['t1'], r32['M82']['t2']), 'label': 'Winner M81 vs M82', 'p1': 'Winner M81', 'p2': 'Winner M82' },
    'M95': { 't1': getW('M86', r32['M86']['t1'], r32['M86']['t2']), 't2': getW('M88', r32['M88']['t1'], r32['M88']['t2']), 'label': 'Winner M86 vs M88', 'p1': 'Winner M86', 'p2': 'Winner M88' },
    'M96': { 't1': getW('M85', r32['M85']['t1'], r32['M85']['t2']), 't2': getW('M87', r32['M87']['t1'], r32['M87']['t2']), 'label': 'Winner M85 vs M87', 'p1': 'Winner M85', 'p2': 'Winner M87' },
}

qf = {
    'M97': { 't1': getW('M89', r16['M89']['t1'], r16['M89']['t2']), 't2': getW('M90', r16['M90']['t1'], r16['M90']['t2']), 'label': 'Winner M89 vs M90', 'p1': 'Winner M89', 'p2': 'Winner M90' },
    'M98': { 't1': getW('M93', r16['M93']['t1'], r16['M93']['t2']), 't2': getW('M94', r16['M94']['t1'], r16['M94']['t2']), 'label': 'Winner M93 vs M94', 'p1': 'Winner M93', 'p2': 'Winner M94' },
    'M99': { 't1': getW('M91', r16['M91']['t1'], r16['M91']['t2']), 't2': getW('M92', r16['M92']['t1'], r16['M92']['t2']), 'label': 'Winner M91 vs M92', 'p1': 'Winner M91', 'p2': 'Winner M92' },
    'M100': { 't1': getW('M95', r16['M95']['t1'], r16['M95']['t2']), 't2': getW('M96', r16['M96']['t1'], r16['M96']['t2']), 'label': 'Winner M95 vs M96', 'p1': 'Winner M95', 'p2': 'Winner M96' },
}

sf = {
    'M101': { 't1': getW('M97', qf['M97']['t1'], qf['M97']['t2']), 't2': getW('M98', qf['M98']['t1'], qf['M98']['t2']), 'label': 'Winner M97 vs M98', 'p1': 'Winner M97', 'p2': 'Winner M98' },
    'M102': { 't1': getW('M99', qf['M99']['t1'], qf['M99']['t2']), 't2': getW('M100', qf['M100']['t1'], qf['M100']['t2']), 'label': 'Winner M99 vs M100', 'p1': 'Winner M99', 'p2': 'Winner M100' },
}

final = {
    'M104': { 't1': getW('M101', sf['M101']['t1'], sf['M101']['t2']), 't2': getW('M102', sf['M102']['t1'], sf['M102']['t2']), 'label': 'Winner M101 vs M102', 'p1': 'Winner M101', 'p2': 'Winner M102' },
}

def loserW(mid, t1, t2):
    w = getW(mid, t1, t2)
    if not t1 or not t2 or not w:
        return None
    return t2 if w == t1 else t1

thirdPlace = {
    'M103': { 't1': loserW('M101', sf['M101']['t1'], sf['M101']['t2']), 't2': loserW('M102', sf['M102']['t1'], sf['M102']['t2']), 'label': 'Loser M101 vs M102', 'p1': 'Loser M101', 'p2': 'Loser M102' }
}

champion = getW('M104', final['M104']['t1'], final['M104']['t2'])
knockout_state = { 'r32': r32, 'r16': r16, 'qf': qf, 'sf': sf, 'final': final, 'thirdPlace': thirdPlace, 'champion': champion }

# Encode the complete state (group picks + bracket picks with one new pick
# applied) into a relative URL, so a full-page reload reconstructs everything.
def state_href(match_id, team):
    gp = urllib.parse.quote(json.dumps(st.session_state.picks))
    new_bp = {k: v for k, v in st.session_state.bracket_picks.items() if v}
    new_bp[match_id] = team
    bp = urllib.parse.quote(json.dumps(new_bp))
    return f'href="?gp={gp}&bp={bp}" target="_self"'

# HTML card generators
def make_html_match_card(match_id, match_data):
    t1, t2 = match_data['t1'], match_data['t2']
    winner = st.session_state.bracket_picks.get(match_id)

    # Reset invalid bracket picks or placeholder picks
    if winner and (winner not in constants.FLAG or (winner != t1 and winner != t2)):
        winner = None
        st.session_state.bracket_picks[match_id] = None

    is_t1_placeholder = (not t1) or (t1 not in constants.FLAG)
    is_t2_placeholder = (not t2) or (t2 not in constants.FLAG)

    display_t1 = f(t1) if t1 else (match_data.get('p1') or "TBD")
    display_t2 = f(t2) if t2 else (match_data.get('p2') or "TBD")

    t1_active_class = "active" if winner == t1 and t1 else ""
    t2_active_class = "active" if winner == t2 and t2 else ""

    t1_clickable_class = "disabled" if is_t1_placeholder else "clickable"
    t2_clickable_class = "disabled" if is_t2_placeholder else "clickable"

    t1_href_attr = state_href(match_id, t1) if not is_t1_placeholder else ''
    t2_href_attr = state_href(match_id, t2) if not is_t2_placeholder else ''
    
    t1_checkmark = '<span style="color: #22c55e; font-weight: bold; font-size: 10px;">✓</span>' if winner == t1 and t1 else ''
    t2_checkmark = '<span style="color: #22c55e; font-weight: bold; font-size: 10px;">✓</span>' if winner == t2 and t2 else ''
    
    return f"""
    <div class="bracket-card">
        <div class="bracket-match-title">
            <span>MATCH {match_id}</span>
            <span style="opacity: 0.7; font-size: 7.5px;">{match_data['label'].replace('Winner ', '').replace('Loser ', '').split(' vs ')[0]}</span>
        </div>
        <a {t1_href_attr} class="bracket-team-row {t1_clickable_class} {t1_active_class}">
            <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 105px;">{display_t1}</span>
            {t1_checkmark}
        </a>
        <a {t2_href_attr} class="bracket-team-row {t2_clickable_class} {t2_active_class}">
            <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 105px;">{display_t2}</span>
            {t2_checkmark}
        </a>
    </div>
    """

def make_html_center_column(state):
    final_card = make_html_match_card('M104', state['final']['M104'])
    third_card = make_html_match_card('M103', state['thirdPlace']['M103'])
    champ = state['champion']
    
    if champ:
        champ_html = f"""
        <div style="width: 100%; background: linear-gradient(135deg, #ca8a04 0%, #16161e 100%); border: 2px solid #f5c518; border-radius: 12px; padding: 14px; text-align: center; box-shadow: 0 0 15px rgba(245, 197, 24, 0.3);">
            <div style="font-size: 9px; font-weight: 800; color: #f5c518; letter-spacing: 0.15em; margin-bottom: 6px; text-transform: uppercase;">
                🏆 WORLD CHAMPION
            </div>
            <div style="font-size: 26px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">{constants.FLAG.get(champ, '🏳️')}</div>
            <div style="font-size: 13px; font-weight: 800; color: #e8e8f0; margin-top: 4px;">{champ}</div>
            <a href="?gp={urllib.parse.quote(json.dumps(st.session_state.picks))}&bp=%7B%7D" target="_self" style="display: inline-block; margin-top: 8px; font-size: 9px; font-weight: 600; color: #6b7280; text-decoration: none; background: #1e1e28; padding: 3px 6px; border-radius: 4px; border: 1px solid #2a2a35;">Reset Bracket</a>
        </div>
        """
    else:
        champ_html = """
        <div style="width: 100%; background-color: #16161e; border: 1px solid #2a2a35; border-radius: 12px; padding: 16px; text-align: center; color: #6b7280; font-style: italic; font-size: 11px; line-height: 1.4; box-shadow: 0 2px 4px rgba(0,0,0,0.12);">
            Crown the champion by predicting all matches
        </div>
        """
        
    return f"""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 175px; min-width: 165px; flex-shrink: 0; height: 100%; gap: 20px;">
        {champ_html}
        <div style="width: 100%;">
            <div style="font-size: 9px; font-weight: 800; color: #6b7280; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px; text-align: center;">FINAL</div>
            {final_card}
        </div>
        <div style="width: 100%;">
            <div style="font-size: 9px; font-weight: 800; color: #6b7280; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px; text-align: center;">3RD PLACE PLAY-OFF</div>
            {third_card}
        </div>
    </div>
    """

# Build the complete tree HTML
tree_html = f"""
<div class="bracket-scroll-container">
    <div class="bracket-flex-layout">
        <!-- COL 1: Left R32 -->
        <div class="bracket-column">
            <div class="bracket-header">Round of 32</div>
            <div class="bracket-matches-flex">
                {make_html_match_card('M74', r32['M74'])}
                {make_html_match_card('M77', r32['M77'])}
                {make_html_match_card('M73', r32['M73'])}
                {make_html_match_card('M75', r32['M75'])}
                {make_html_match_card('M83', r32['M83'])}
                {make_html_match_card('M84', r32['M84'])}
                {make_html_match_card('M81', r32['M81'])}
                {make_html_match_card('M82', r32['M82'])}
            </div>
        </div>
        
        <!-- COL 2: Left R16 -->
        <div class="bracket-column">
            <div class="bracket-header">Round of 16</div>
            <div class="bracket-matches-flex">
                {make_html_match_card('M89', r16['M89'])}
                {make_html_match_card('M90', r16['M90'])}
                {make_html_match_card('M93', r16['M93'])}
                {make_html_match_card('M94', r16['M94'])}
            </div>
        </div>
        
        <!-- COL 3: Left QF -->
        <div class="bracket-column">
            <div class="bracket-header">Quarter-Finals</div>
            <div class="bracket-matches-flex">
                {make_html_match_card('M97', qf['M97'])}
                {make_html_match_card('M98', qf['M98'])}
            </div>
        </div>
        
        <!-- COL 4: Left SF -->
        <div class="bracket-column">
            <div class="bracket-header">Semi-Finals</div>
            <div class="bracket-matches-flex">
                {make_html_match_card('M101', sf['M101'])}
            </div>
        </div>
        
        <!-- COL 5: Center Column -->
        {make_html_center_column(knockout_state)}
        
        <!-- COL 6: Right SF -->
        <div class="bracket-column">
            <div class="bracket-header">Semi-Finals</div>
            <div class="bracket-matches-flex">
                {make_html_match_card('M102', sf['M102'])}
            </div>
        </div>
        
        <!-- COL 7: Right QF -->
        <div class="bracket-column">
            <div class="bracket-header">Quarter-Finals</div>
            <div class="bracket-matches-flex">
                {make_html_match_card('M99', qf['M99'])}
                {make_html_match_card('M100', qf['M100'])}
            </div>
        </div>
        
        <!-- COL 8: Right R16 -->
        <div class="bracket-column">
            <div class="bracket-header">Round of 16</div>
            <div class="bracket-matches-flex">
                {make_html_match_card('M91', r16['M91'])}
                {make_html_match_card('M92', r16['M92'])}
                {make_html_match_card('M95', r16['M95'])}
                {make_html_match_card('M96', r16['M96'])}
            </div>
        </div>
        
        <!-- COL 9: Right R32 -->
        <div class="bracket-column">
            <div class="bracket-header">Round of 32</div>
            <div class="bracket-matches-flex">
                {make_html_match_card('M76', r32['M76'])}
                {make_html_match_card('M78', r32['M78'])}
                {make_html_match_card('M79', r32['M79'])}
                {make_html_match_card('M80', r32['M80'])}
                {make_html_match_card('M86', r32['M86'])}
                {make_html_match_card('M88', r32['M88'])}
                {make_html_match_card('M85', r32['M85'])}
                {make_html_match_card('M87', r32['M87'])}
            </div>
        </div>
    </div>
</div>
"""

# Render bracket directly in the main document (NOT an iframe) so the
# <a href="?match_id=..."> links can navigate the page. Streamlit's
# components.html() iframe is sandboxed without top-navigation, which
# silently blocks those links. The bracket CSS classes are already
# defined in the page-level <style> block above.
#
# st.markdown runs content through a Markdown parser first: lines indented
# 4+ spaces become code blocks and blank lines split the HTML into separate
# blocks. Strip per-line indentation and drop blank lines so the whole tree
# is parsed as a single raw-HTML block instead of printed as code.
tree_html_clean = "\n".join(ln.strip() for ln in tree_html.splitlines() if ln.strip())
st.markdown(tree_html_clean, unsafe_allow_html=True)

# ── SECTION 3: Projected Group Standings ──
st.markdown('<div class="section-title">3. Projected Group Standings</div>', unsafe_allow_html=True)

groups_cols = st.columns(4)
for idx, gKey in enumerate(group_keys):
    col_idx = idx % 4
    st_teams = all_group_standings[gKey]
    is_settled = gKey in ["A", "B", "C", "D", "E", "F"]

    with groups_cols[col_idx]:
        with st.container(border=True):
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2a2a35; padding-bottom: 6px; margin-bottom: 8px;">
                <span style="font-weight: 800; font-size: 13px; color: #e8e8f0;">GROUP {gKey}</span>
                <span style="font-size: 9px; font-weight: 700; color: {'#22c55e' if is_settled else '#3b82f6'}; background: {'rgba(34, 197, 94, 0.1)' if is_settled else 'rgba(59, 130, 246, 0.1)'}; padding: 2px 6px; border-radius: 4px; text-transform: uppercase;">
                    {'Settled' if is_settled else 'Live'}
                </span>
            </div>

            <div style="display: flex; font-size: 9px; color: #6b7280; font-weight: 800; border-bottom: 1px solid #1a1a24; padding-bottom: 4px; margin-bottom: 4px;">
                <span style="width: 14px;">#</span>
                <span style="flex: 1;">TEAM</span>
                <span style="width: 22px; text-align: right;">PTS</span>
                <span style="width: 26px; text-align: right;">GD</span>
                <span style="width: 22px; text-align: right;">GF</span>
            </div>
            """, unsafe_allow_html=True)

            for i, t in enumerate(st_teams):
                is_3rd_qual = (i == 2 and any(x['name'] == t['name'] and x['qualifies'] for x in all_thirds))
                qual = (i < 2 or is_3rd_qual)

                rank_color = "#22c55e" if i < 2 else ("#f5c518" if is_3rd_qual else "#6b7280")
                bg_style = "background-color: rgba(34, 197, 94, 0.05);" if is_3rd_qual else "background-color: transparent;"
                team_text_weight = "bold" if qual else "normal"
                team_text_color = "#e8e8f0" if qual else "#6b7280"

                st.markdown(f"""
                <div style="display: flex; align-items: center; padding: 4px 6px; border-radius: 6px; {bg_style} font-size: 12px; gap: 4px;">
                    <span style="width: 12px; font-weight: bold; color: {rank_color};">{i+1}</span>
                    <span style="flex: 1; font-weight: {team_text_weight}; color: {team_text_color}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{f(t['name'])}</span>
                    <span style="width: 22px; font-weight: {team_text_weight}; color: {team_text_color}; text-align: right;">{t['pts']}</span>
                    <span style="width: 26px; color: {team_text_color}; text-align: right;">{fmt_gd(t['gd'])}</span>
                    <span style="width: 22px; color: #6b7280; text-align: right;">{t['gf']}</span>
                </div>
                """, unsafe_allow_html=True)
