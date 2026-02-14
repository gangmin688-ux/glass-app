import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 1. 기본 설정 및 종목 매핑 ---
GEMINI_API_KEY = "AIzaSyCjU57YfYEgX07zvd-nFtooE9VJG-wS2UE"
MODEL_NAME = "gemini-2.5-flash"

st.set_page_config(page_title="노강민의 주식 에이전트", page_icon="📈", layout="wide")

# 한글 종목명 -> 티커 변환 사전 (필요한 종목 계속 추가 가능)
KOREA_STOCKS = {
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS",
    "카카오": "035720.KS", "네이버": "035420.KS", "NAVER": "035420.KS",
    "에코프로": "086520.KQ", "에코프로비엠": "247540.KQ", "기아": "000270.KS",
    "셀트리온": "068270.KS", "포스코홀딩스": "005490.KS", "HLB": "028300.KQ"
}

# --- 2. 데이터 초기화 ---
if 'users' not in st.session_state:
    st.session_state.users = {
        "노강민": {"pw": "1203", "slack": "https://hooks.slack.com/services/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", "watchlist": ["NVDA", "005930.KS"]},
        "엄윤선": {"pw": "0224", "slack": "https://hooks.slack.com/services/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", "watchlist": ["TSLA"]},
        "노영신": {"pw": "0417", "slack": "", "watchlist": ["AAPL"]}
    }
if 'alarm_list' not in st.session_state:
    st.session_state.alarm_list = []
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None

# --- 3. 유틸리티 함수 ---
def convert_ticker(name):
    return KOREA_STOCKS.get(name.strip(), name.strip().upper())

def get_live_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="2d")
        if len(data) >= 2:
            curr = data['Close'].iloc[-1]
            diff = curr - data['Close'].iloc[-2]
            pct = (diff / data['Close'].iloc[-2]) * 100
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

# --- 4. 로그인 체크 ---
if st.session_state.logged_in_user is None:
    st.title("🔐 주식 에이전트 로그인")
    u_choice = st.selectbox("멤버 선택", list(st.session_state.users.keys()))
    u_pw = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if u_pw == st.session_state.users[u_choice]["pw"]:
            st.session_state.logged_in_user = u_choice
            st.rerun()
        else: st.error("비밀번호가 틀렸습니다.")
    st.stop()

# --- 5. 로그인 성공 후 화면 ---
current_user = st.session_state.logged_in_user
my_data = st.session_state.users[current_user]

st.sidebar.title(f"👤 {current_user}님")
if st.sidebar.button("로그아웃"):
    st.session_state.logged_in_user = None
    st.rerun()

menu = st.sidebar.selectbox("메뉴", ["🚀 AI 분석 & 전송", "⭐ 관심 종목 & 차트", "🧮 수익률 계산기", "🔥 시장 트렌드", "⏰ 정기 알람", "💬 피드백", "⚙️ 개인 설정"])

# [1] AI 분석 & 전송
if menu == "🚀 AI 분석 & 전송":
    st.title("🤖 AI 뉴스 분석 및 슬랙 전송")
    target_name = st.text_input("분석할 종목명(한글/티커)", "삼성전자")
    if st.button("🔍 뉴스 분석 시작"):
        ticker = convert_ticker(target_name)
        with st.spinner(f"{target_name} 분석 중..."):
            stock = yf.Ticker(ticker)
            news_titles = [n.get('title', '') for n in stock.news[:3]]
            news_text = "\n".join(news_titles) if news_titles else "최신 뉴스가 없습니다."
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
            payload = {"contents": [{"parts": [{"text": f"{target_name}({ticker}) 주식 뉴스 분석:\n{news_text}"}]}]}
            res = requests.post(url, json=payload).json()
            analysis = res['candidates'][0]['content']['parts'][0]['text']
            st.session_state[f"last_ai_{current_user}"] = (target_name, analysis)

    if f"last_ai_{current_user}" in st.session_state:
        t, a = st.session_state[f"last_ai_{current_user}"]
        st.info(f"**[{t} 리포트]**\n\n{a}")
        if st.button("📤 내 슬랙으로 전송"):
            if send_slack(my_data["slack"], f"📢 {current_user}의 AI 리포트: {a}"):
                st.success("슬랙 전송 성공!")
            else: st.error("슬랙 URL을 설정해주세요.")

# [2] 관심 종목 & 차트
elif menu == "⭐ 관심 종목 & 차트":
    st.title("⭐ 실시간 시세판")
    c1, c2, c3 = st.columns([3,1,1])
    add_input = c1.text_input("종목명/코드 추가", placeholder="예: 카카오, TSLA")
    if c2.button("➕ 등록") and add_input:
        tk = convert_ticker(add_input)
        if tk not in my_data["watchlist"]:
            my_data["watchlist"].append(tk); st.rerun()
    if c3.button("🔄 새로고침"): st.rerun()

    st.divider()
    cols = st.columns(3)
    for i, s in enumerate(my_data["watchlist"]):
        p, d, pct = get_live_price(s)
        with cols[i % 3]:
            if p:
                unit = "원" if ".KS" in s or ".KQ" in s else "$"
                st.metric(s, f"{p:,.0f}{unit}" if unit=="원" else f"${p:,.2f}", f"{pct:.2f}%")
                cb1, cb2 = st.columns(2)
                if cb1.button(f"📈 차트", key=f"ch_{s}"): st.session_state.sel_chart = s
                if cb2.button(f"❌ 삭제", key=f"dl_{s}"): 
                    my_data["watchlist"].remove(s); st.rerun()

    if 'sel_chart' in st.session_state:
        target = st.session_state.sel_chart
        df = yf.Ticker(target).history(period="1mo")
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(title=f"{target} 상세 차트", template="plotly_white", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        if st.button("차트 닫기"): del st.session_state.sel_chart; st.rerun()

# [3] 수익률 계산기
elif menu == "🧮 수익률 계산기":
    st.title("💸 내 수익률 계산기")
    cur_type = st.radio("통화", ["KRW(원)", "USD($)"], horizontal=True)
    sym = "₩" if "KRW" in cur_type else "$"
    col1, col2 = st.columns(2)
    buy_p = col1.number_input(f"매수단가 ({sym})", value=50000.0)
    qty = col2.number_input("보유수량", value=10)
    now_p = col1.number_input(f"현재가 ({sym})", value=55000.0)
    fee = col2.number_input("수수료(%)", value=0.015, format="%.3f")
    
    total_buy = buy_p * qty
    total_now = now_p * qty
    profit = total_now - total_buy - (total_now * fee / 100)
    st.divider()
    m1, m2 = st.columns(2)
    m1.metric("예상 수익금", f"{sym}{profit:,.0f}")
    m2.metric("수익률", f"{(profit/total_buy)*100:.2f}%")

# [4] 시장 트렌드
elif menu == "🔥 시장 트렌드":
    st.title("📊 글로벌 핫 이슈 종목")
    if st.button("🔥 트렌드 분석"):
        with st.spinner("AI가 분석 중..."):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
            payload = {"contents": [{"parts": [{"text": "오늘 가장 화제인 주식 종목 3개와 이유를 한국어로 알려줘."}]}]}
            res = requests.post(url, json=payload).json()
            st.info(res['candidates'][0]['content']['parts'][0]['text'])

# [5] 정기 알람
elif menu == "⏰ 정기 알람":
    st.title("⏰ 분석 알람 예약")
    a_time = st.time_input("시간 설정")
    a_stocks = st.text_input("알람 받을 종목들(쉼표 구분)", "삼성전자, NVDA")
    if st.button("알람 등록"):
        st.session_state.alarm_list.append({"user": current_user, "time": a_time.strftime("%H:%M"), "stocks": a_stocks})
        st.success("알람이 등록되었습니다!")
    st.subheader("내 알람 목록")
    for a in st.session_state.alarm_list:
        if a['user'] == current_user:
            st.write(f"🔔 {a['time']} | 📦 {a['stocks']}")

# [6] 피드백
elif menu == "💬 피드백":
    st.title("💬 개발자(노강민)에게 한마디")
    msg = st.text_area("불편한 점이나 추가하고 싶은 기능을 적어주세요.")
    if st.button("의견 보내기"):
        if send_slack(st.session_state.users["노강민"]["slack"], f"📝 [{current_user} 피드백]: {msg}"):
            st.success("노강민 님에게 피드백이 전송되었습니다!")

# [7] 개인 설정
elif menu == "⚙️ 개인 설정":
    st.title("⚙️ 내 정보 수정")
    new_pw = st.text_input("비밀번호 변경", value=my_data["pw"], type="password")
    new_url = st.text_input("슬랙 Webhook URL", value=my_data["slack"])
    if st.button("저장하기"):
        my_data["pw"] = new_pw
        my_data["slack"] = new_url
        st.success("수정 완료!")
