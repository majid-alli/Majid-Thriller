# Multi-language Thriller Streaming Recommender — Streamlit

import streamlit as st
import requests
import time
from typing import Dict, Optional, Tuple

TMDB_API_KEY = "f6f362ba2df690f3c13fb52e3f0e05db"  # Replace with your TMDb key

if not TMDB_API_KEY:
    st.error("Please set your TMDb API key inside the script (line near top).")
    st.stop()

st.set_page_config(page_title="Thriller Movie Recommender", page_icon="🎬", layout="wide")
st.title("🎬 Thriller Movie Recommender")
st.caption("Find thriller movies (IMDb ≥ 7) on Netflix, Disney+ Hotstar, Amazon Prime Video, and ZEE5 (India). Choose language preference.")

TMDB_BASE = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p/w500"

@st.cache_data(ttl=3600)
def tmdb_get(path: str, params: Dict) -> Dict:
    params = dict(params or {})
    params["api_key"] = TMDB_API_KEY
    r = requests.get(f"{TMDB_BASE}{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=3600)
def discover_movies(page: int, min_votes: int, language_filter: str) -> Dict:
    params = {
        "sort_by": "popularity.desc",
        "with_genres": "53",  # Thriller genre
        "include_adult": "false",
        "page": page,
        "vote_count.gte": min_votes,
        "region": "IN"
    }
    if language_filter:
        params["with_original_language"] = language_filter
    return tmdb_get("/discover/movie", params)

@st.cache_data(ttl=3600)
def get_watch_providers(movie_id: int) -> Dict:
    return tmdb_get(f"/movie/{movie_id}/watch/providers", {})

def available_on_in(providers_json: Dict, wanted: list) -> Tuple[bool, list]:
    found = []
    if not providers_json:
        return False, found
    results = providers_json.get("results", {})
    IN = results.get("IN") or {}
    buckets = []
    for key in ["flatrate", "ads", "free", "rent", "buy"]:
        if IN.get(key):
            buckets.extend(IN.get(key))
    names = {p.get("provider_name", "").lower() for p in buckets}

    for p in wanted:
        if p.lower() == "netflix" and any("netflix" in n for n in names):
            found.append(p)
        elif p.lower() == "disney+ hotstar" and any("hotstar" in n or "disney" in n for n in names):
            found.append(p)
        elif p.lower() == "amazon prime video" and any("prime" in n or "amazon" in n for n in names):
            found.append(p)
        elif p.lower() == "zee5" and any("zee5" in n for n in names):
            found.append(p)
    return (len(found) > 0), found

st.sidebar.header("Settings")
min_votes = st.sidebar.slider("Minimum number of votes", 50, 1000, 100)
pages_to_fetch = st.sidebar.slider("Pages to fetch from TMDb", 1, 5, 2)
selected_platforms = st.sidebar.multiselect(
    "Select platforms:",
    ["Netflix", "Disney+ Hotstar", "Amazon Prime Video", "ZEE5"],
    default=["Netflix", "Disney+ Hotstar", "Amazon Prime Video", "ZEE5"]
)
language_choice = st.sidebar.radio(
    "Select language:",
    ["All", "Hindi", "English", "Tamil", "Telugu", "Malayalam"],
    index=0
)
language_filter = ""
if language_choice == "Hindi":
    language_filter = "hi"
elif language_choice == "English":
    language_filter = "en"
elif language_choice == "Tamil":
    language_filter = "ta"
elif language_choice == "Telugu":
    language_filter = "te"
elif language_choice == "Malayalam":
    language_filter = "ml"

if st.sidebar.button("Find Thrillers"):
    with st.spinner("Fetching movies..."):
        movies = []
        for page in range(1, pages_to_fetch + 1):
            try:
                data = discover_movies(page, min_votes, language_filter)
            except Exception as e:
                st.error(f"Error fetching movies: {e}")
                continue
            for m in data.get("results", []):
                providers = get_watch_providers(m["id"])
                avail, found_platforms = available_on_in(providers, selected_platforms)
                if not avail:
                    continue
                if m.get("vote_average", 0) < 7:
                    continue
                movies.append({
                    "title": m.get("title"),
                    "rating": m.get("vote_average"),
                    "poster": f"{IMG_BASE}{m['poster_path']}" if m.get("poster_path") else None,
                    "platforms": found_platforms,
                    "url": f"https://www.themoviedb.org/movie/{m['id']}"
                })
                time.sleep(0.2)

        if not movies:
            st.warning("No thriller movies found matching criteria.")
        else:
            st.success(f"Found {len(movies)} thriller movies!")
            cols = st.columns(4)
            for idx, movie in enumerate(movies):
                c = cols[idx % 4]
                with c:
                    if movie["poster"]:
                        st.image(movie["poster"], use_container_width=True)
                    st.markdown(f"**[{movie['title']}]({movie['url']})**")
                    st.caption(f"IMDb: {movie['rating']:.1f}")
                    st.caption(f"Platforms: {', '.join(movie['platforms'])}")
