import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. 기본 설정 ---
GEMINI_API_KEY = "AIzaSyCjU57YfYEgX07zvd-nFtooE9VJG-wS2UE"
MODEL_NAME = "gemini-2.5-flash"

st.set_page_config(page_title="노강민의 주식 에이전트", page_icon="📈", layout="wide")

# --- 2. 데이터 초기화 (사용자별 독립 세션) ---
if 'users' not in st.session_state:
    st.session_state.users = {
        "노강민": {"pw": "0000", "slack": "https://hooks.slack.com/services/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", "watchlist": ["NVDA", "TSLA"]},
        "엄윤선": {"pw": "0224", "slack": "https://hooks.slack.com/services/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", "watchlist": ["AAPL"]},
        "노영신": {"pw": "0417", "slack": "", "watchlist": ["005930.KS"]}
    }
if 'alarm_list' not in st.session_state:
    st.session_state.alarm_list = []
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None

# --- 3. 유틸리티 함수 ---
def get_live_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="2d")
        if len(data) >= 2:
            curr = data['Close'].iloc[-1]
            prev = data['Close'].iloc[-2]
            diff = curr - prev
            pct = (diff / prev) * 100
            return curr, diff, pct
        return None, None, None
    except: return None, None, None

def send_slack(url, msg):
    if url:
        try:
            requests.post(url, json={"text": msg})
            return True
        except: return False
    return False

# --- 4. 로그인 로직 ---
if st.session_state.logged_in_user is None:
    st.title("🔐 주식 에이전트 로그인")
    col1, col2 = st.columns([1, 1])
    with col1:
        u_choice = st.selectbox("멤버 선택", list(st.session_state.users.keys()))
        u_pw = st.text_input("비밀번호", type="password")
        if st.button("로그인"):
            if u_pw == st.session_state.users[u_choice]["pw"]:
                st.session_state.logged_in_user = u_choice
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
    st.stop()

# --- 5. 로그인 후 메인 화면 ---
current_user = st.session_state.logged_in_user
my_data = st.session_state.users[current_user]

# 사이드바 메뉴
st.sidebar.title(f"👤 {current_user}님")
if st.sidebar.button("로그아웃"):
    st.session_state.logged_in_user = None
    st.rerun()

st.sidebar.divider()
menu = st.sidebar.selectbox("메뉴", ["🚀 AI 분석 & 전송", "⭐ 관심 종목 & 차트", "🧮 수익률 계산기", "🔥 시장 트렌드", "⏰ 정기 알람", "💬 피드백", "⚙️ 개인 설정"])

# [메뉴 1: AI 분석]
if menu == "🚀 AI 분석 & 전송":
    st.title("🤖 AI 뉴스 분석실")
    ticker = st.text_input("종목 코드 입력", "NVDA").upper()
    if st.button("🔍 분석 시작"):
        with st.spinner("AI가 뉴스를 분석 중입니다..."):
            stock = yf.Ticker(ticker)
            news_text = "\n".join([n.get('title', '') for n in stock.news[:3]])
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
            payload = {"contents": [{"parts": [{"text": f"{ticker} 주식 분석 및 전망:\n{news_text}"}]}]}
            res = requests.post(url, json=payload).json()
            st.session_state[f"ai_res_{current_user}"] = (ticker, res['candidates'][0]['content']['parts'][0]['text'])

    if f"ai_res_{current_user}" in st.session_state:
        t, a = st.session_state[f"ai_res_{current_user}"]
        st.info(f"**[{t} 분석 보고서]**\n\n{a}")
        if st.button("📤 내 슬랙으로 전송"):
            if send_slack(my_data["slack"], f"📢 AI 리포트: {a}"): st.success("전송 완료!")
            else: st.error("슬랙 URL을 확인해주세요.")

# [메뉴 2: 관심 종목 & 차트]
elif menu == "⭐ 관심 종목 & 차트":
    st.title("⭐ 실시간 시세 및 차트")
    c1, c2, c3 = st.columns([3, 1, 1])
    add_s = c1.text_input("종목 추가", placeholder="AAPL").upper()
    if c2.button("등록") and add_s:
        if add_s not in my_data["watchlist"]:
            my_data["watchlist"].append(add_s); st.rerun()
    if c3.button("🔄 새로고침"): st.rerun()

    st.divider()
    cols = st.columns(3)
    for i, s in enumerate(my_data["watchlist"]):
        p, d, pct = get_live_price(s)
        with cols[i % 3]:
            if p:
                st.metric(s, f"{p:,.2f}", f"{pct:.2f}%")
                if st.button(f"📈 차트", key=f"ch_{s}"): st.session_state.sel_chart = s
                if st.button(f"❌ 삭제", key=f"dl_{s}"): 
                    my_data["watchlist"].remove(s); st.rerun()

    if 'sel_chart' in st.session_state:
        target = st.session_state.sel_chart
        df = yf.Ticker(target).history(period="1mo")
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(title=f"{target} 1개월 차트", xaxis_rangeslider_visible=False, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
        if st.button("차트 닫기"): del st.session_state.sel_chart; st.rerun()

# [메뉴 3: 수익률 계산기]
elif menu == "🧮 수익률 계산기":
    st.title("💸 수익률 계산기")
    col1, col2 = st.columns(2)
    buy_p = col1.number_input("매수 단가", value=100.0)
    qty = col2.number_input("수량", value=10)
    curr_p = col1.number_input("현재가", value=110.0)
    fee = col2.number_input("수수료(%)", value=0.015)
    
    total_buy = buy_p * qty
    total_now = curr_p * qty
    profit = total_now - total_buy - (total_now * fee / 100)
    st.metric("수익금", f"{profit:,.2f}", f"{(profit/total_buy)*100:.2f}%")

# [메뉴 4: 시장 트렌드]
elif menu == "🔥 시장 트렌드":
    st.title("🔥 AI 추천 핫 종목")
    if st.button("트렌드 읽기"):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": "현재 핫한 미국 주식 3개 티커와 이유 요약해줘."}]}]}
        res = requests.post(url, json=payload).json()
        st.write(res['candidates'][0]['content']['parts'][0]['text'])

# [메뉴 5: 정기 알람]
elif menu == "⏰ 정기 알람":
    st.title("⏰ 알람 예약")
    t_in = st.time_input("시간")
    s_in = st.text_input("종목(쉼표 구분)")
    if st.button("알람 추가"):
        st.session_state.alarm_list.append({"user": current_user, "time": t_in.strftime("%H:%M"), "stocks": s_in.split(",")})
        st.success("등록 완료")
    for a in st.session_state.alarm_list:
        if a['user'] == current_user: st.write(f"⏰ {a['time']} - {a['stocks']}")

# [메뉴 6: 피드백]
elif menu == "💬 피드백":
    st.title("💬 피드백")
    f_text = st.text_area("건의사항")
    if st.button("전송"):
        send_slack(st.session_state.users["노강민"]["slack"], f"피드백: {f_text}")
        st.success("운영자에게 전송됨")

# [메뉴 7: 개인 설정]
elif menu == "⚙️ 개인 설정":
    st.title("⚙️ 설정")
    new_pw = st.text_input("비밀번호 변경", value=my_data["pw"], type="password")
    new_url = st.text_input("슬랙 URL", value=my_data["slack"])
    if st.button("저장"):
        my_data["pw"] = new_pw
        my_data["slack"] = new_url
        st.success("저장되었습니다.")