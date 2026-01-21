import streamlit as st
import google.generativeai as genai
import twstock
import requests
import json

# --- 頁面基本設定 ---
st.set_page_config(page_title="AI 股市全方位分析 (終極修正版)", page_icon="📈", layout="wide")

# --- 側邊欄：API Key 設定 ---
with st.sidebar:
    st.header("⚙️ 系統設定")
    gemini_key = st.text_input("Gemini API Key", type="password", key="gemini_key")
    serper_key = st.text_input("Serper API Key", type="password", key="serper_key")
    st.markdown("---")
    st.caption("若遇到 404 錯誤，通常是 API Key 權限或套件版本問題，本系統已啟用自動模型偵測功能。")

# --- 核心功能 1: 聰明選擇可用的 AI 模型 ---
def get_gemini_model():
    """
    自動偵測帳號可用的模型，避免 404 錯誤
    """
    try:
        genai.configure(api_key=gemini_key)
        # 列出所有可用模型
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # 策略：優先尋找 Flash (快/便宜)，其次 Pro，最後隨便選一個
        target_model = None
        
        # 1. 找 gemini-1.5-flash
        for m in available_models:
            if 'gemini-1.5-flash' in m:
                target_model = m
                break
        
        # 2. 如果沒 Flash，找 gemini-pro
        if not target_model:
            for m in available_models:
                if 'gemini-pro' in m or 'gemini-1.5-pro' in m:
                    target_model = m
                    break
        
        # 3. 如果都沒有，就拿第一個能用的
        if not target_model and available_models:
            target_model = available_models[0]
            
        if target_model:
            # st.toast(f"✅ 已自動切換至模型：{target_model}", icon="🤖")
            return genai.GenerativeModel(target_model)
        else:
            st.error("❌ 找不到任何可用的 Gemini 模型，請檢查 API Key 是否有效。")
            return None
            
    except Exception as e:
        st.error(f"❌ 模型設定失敗: {str(e)}")
        return None

# --- 核心功能 2: 股票代號識別 ---
def resolve_stock_id(ticker_input, market):
    ticker = ticker_input.strip().upper()
    name = ticker 
    if market == "台灣 (TW)":
        if ticker in twstock.codes:
            stock_info = twstock.codes[ticker]
            name = stock_info.name
            st.toast(f"✅ 成功辨識：{ticker} -> {name}")
            return ticker, name
        else:
            return ticker, ticker
    return ticker, ticker

# --- 核心功能 3: Serper 搜尋 ---
def search_news_serper(query, api_key):
    url = "https://google.serper.dev/search"
    if "新聞" in query:
        gl, hl = "tw", "zh-tw"
    else:
        gl, hl = "us", "en"

    payload = json.dumps({
        "q": query, "gl": gl, "hl": hl, "num": 5, "tbs": "qdr:w"
    })
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, data=payload)
        return response.json() if response.status_code == 200 else {"error": str(response.status_code)}
    except Exception as e:
        return {"error": str(e)}

# --- 核心功能 4: AI 分析報告 ---
def generate_analysis(model, news_text, ticker, name):
    prompt = f"""
    你是一位華爾街資深操盤手。請根據以下【過去一週最新搜尋資料】，分析「{name} ({ticker})」。
    
    【搜尋資料】：
    {news_text}
    
    請以**繁體中文**撰寫分析：
    1. **🔥 市場焦點**：條列最近發生的關鍵事件（營收、產品、外資動向...）。
    2. **⚖️ 多空分析**：
       - ✅ 利多理由 (2-3點)
       - 🔻 風險隱憂 (2-3點)
    3. **🎯 投資建議**：(強力買進 / 分批佈局 / 觀望 / 賣出) 並簡述理由。
    
    若無明確資訊，請誠實告知。
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"生成失敗: {str(e)}"

# --- 主程式 ---
st.title("🤖 AI 股市投資助手 (自動模型偵測版)")

col1, col2 = st.columns([1, 1])
with col1:
    ticker_input = st.text_input("輸入股票代號", placeholder="例如: 2330, 2603, NVDA")
with col2:
    market_select = st.selectbox("選擇市場", ["台灣 (TW)", "美國 (US)"])

if st.button("🚀 開始智能分析", type="primary"):
    if not gemini_key or not serper_key:
        st.error("❌ 請輸入 Gemini 與 Serper API Key")
    elif not ticker_input:
        st.warning("⚠️ 請輸入股票代號")
    else:
        # 1. 準備模型 (自動偵測)
        model = get_gemini_model()
        
        if model:
            # 2. 識別股票
            real_ticker, real_name = resolve_stock_id(ticker_input, market_select)
            
            # 3. 搜尋
            query = f"{real_name} {real_ticker} 股價 新聞 營收" if market_select == "台灣 (TW)" else f"{real_ticker} stock news analysis"
            st.info(f"🔎 正在搜尋：{query}")
            search_res = search_news_serper(query, serper_key)
            
            # 4. 處理結果
            if "error" in search_res:
                st.error(f"搜尋錯誤: {search_res['error']}")
            elif not search_res.get("organic"):
                st.warning("找不到相關資料。")
            else:
                # 整理文字
                news_text = "\n".join([f"{i+1}. {r.get('title')} - {r.get('snippet')}" for i, r in enumerate(search_res['organic'])])
                
                with st.spinner("🧠 AI 正在分析資料..."):
                    report = generate_analysis(model, news_text, real_ticker, real_name)
                
                st.success("✅ 分析完成")
                st.markdown(report)
                with st.expander("查看原始搜尋資料"):
                    st.text(news_text)
