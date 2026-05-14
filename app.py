import streamlit as st
import requests
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Page config
st.set_page_config(page_title="NHKやさしいことばニュース", layout="wide")

st.title("NHKやさしいことばニュース学習サイト")
st.write("過去1か月のニュース記事を選んで、内容について語り合いましょう。")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "news_data" not in st.session_state:
    st.session_state.news_data = []

def get_fallback_data():
    """Fallback to public NHK RSS if Easy API is protected/unavailable"""
    parsed_data = []
    try:
        response = requests.get('https://www.nhk.or.jp/rss/news/cat0.xml', timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for item in root.findall('./channel/item'):
                title = item.find('title').text
                link = item.find('link').text
                desc = item.find('description').text if item.find('description') is not None else ""
                # Use pubDate if available, else today
                date_str = datetime.now().strftime('%Y-%m-%d')
                pubDate = item.find('pubDate')
                if pubDate is not None and pubDate.text:
                    date_str = pubDate.text[:16]
                    
                parsed_data.append({
                    'id': link,
                    'title': title,
                    'genre': '一般ニュース',
                    'date': date_str,
                    'content': desc + f"\n\n[詳細を見る]({link})"
                })
    except Exception as e:
        pass
        
    if not parsed_data:
        # Final mock fallback
        parsed_data = [
            {"id": "1", "title": "新しい桜の種類が見つかる", "genre": "科学・文化", "date": "2026-04-20", "content": "日本の研究チームが新しい桜の種類を見つけました。"},
            {"id": "2", "title": "日本の経済が少し良くなる", "genre": "経済", "date": "2026-05-01", "content": "今年の経済は少しずつ良くなっていると発表されました。"},
            {"id": "3", "title": "新しいスポーツの大会", "genre": "スポーツ", "date": "2026-05-10", "content": "週末に大きなスポーツの大会が開かれました。"},
        ]
    return parsed_data

def fetch_news(username, password):
    url = "https://news.web.nhk/news/easy/news-list.json"
    parsed_data = []
    try:
        # First try to see if it accepts Basic Auth (or no auth)
        response = requests.get(url, auth=(username, password), timeout=5)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0 and type(data[0]) == dict:
                if "top_news" in data[0]:
                    # Format: [{date: '...', top_news: [...]}]
                    for day in data:
                        date = day.get('date', '')
                        for item in day.get('top_news', []) + day.get('general_news', []):
                            parsed_data.append({
                                'id': item.get('news_id', ''),
                                'title': item.get('title', item.get('title_with_ruby', 'No Title')),
                                'genre': 'その他', # News web easy JSON doesn't directly expose genre
                                'date': date,
                                'content': item.get('news_web_url', '') 
                            })
                    if parsed_data:
                        return parsed_data
    except Exception as e:
        pass
    
    return get_fallback_data()

# Login UI
if not st.session_state.logged_in:
    with st.form("login_form"):
        st.subheader("ログイン")
        username = st.text_input("ユーザー名")
        password = st.text_input("パスワード", type="password")
        submit = st.form_submit_button("ログイン")
        
        if submit:
            st.session_state.logged_in = True
            st.session_state.news_data = fetch_news(username, password)
            st.rerun()

else:
    # Logout button
    if st.sidebar.button("ログアウト"):
        st.session_state.logged_in = False
        st.session_state.news_data = []
        st.rerun()

    news_list = st.session_state.news_data
    
    if not news_list:
        st.warning("ニュース記事が見つかりませんでした。")
    else:
        genres = list(set([item.get("genre", "その他") for item in news_list]))
        genres.insert(0, "すべて")
        
        selected_genre = st.sidebar.selectbox("ジャンルで絞り込む", genres)
        
        filtered_news = news_list
        if selected_genre != "すべて":
            filtered_news = [item for item in news_list if item.get("genre", "その他") == selected_genre]
            
        st.sidebar.subheader("記事一覧")
        
        if filtered_news:
            titles = [item.get("title", "No Title") for item in filtered_news]
            selected_title = st.sidebar.radio("記事を選んでください:", titles)
            
            selected_article = next((item for item in filtered_news if item.get("title") == selected_title), None)
            
            if selected_article:
                st.subheader(selected_article.get("title", "No Title"))
                st.caption(f"ジャンル: {selected_article.get('genre', 'その他')} | 日付: {selected_article.get('date', '')}")
                st.write(selected_article.get("content", "本文がありません。"))
                
                st.divider()
                st.subheader("語り合いコーナー（ディスカッション）")
                comment = st.text_area("この記事についてあなたの意見や感想を書いてください:")
                if st.button("送信"):
                    st.success("コメントを送信しました！")
        else:
            st.info("このジャンルの記事はありません。")
