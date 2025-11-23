import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
import openai
import os

st.set_page_config(page_title="AI기반 여행 플래너", layout="wide")

# -------------------------------
# API 키
# -------------------------------
OPEN_WEATHER_API_KEY = "82634aa21c485c6bb6c2d4e3adef0b45"
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
openai.api_key = OPENAI_API_KEY

# -------------------------------
# 도시 좌표 및 소개
# -------------------------------
CITY_COORDS = {
    "서울": (37.5665, 126.9780),
    "부산": (35.1796, 129.0756),
    "제주": (33.4996, 126.5312),
    "도쿄": (35.6895, 139.6917),
    "오사카": (34.6937, 135.5023),
    "파리": (48.8566, 2.3522)
}

CITY_INTRO = {
    "서울": "서울은 대한민국의 수도로, 역사와 현대가 공존하는 도시입니다. 경복궁, 남산타워, 한강공원 등 다양한 관광지가 있으며, 맛집과 쇼핑, 문화 체험을 모두 즐길 수 있습니다.",
    "부산": "부산은 한국의 대표 항구 도시로, 해운대, 광안리, 자갈치 시장 등 아름다운 해변과 활기찬 시장을 즐길 수 있습니다.",
    "제주": "제주는 한국의 대표 관광 섬으로, 아름다운 자연경관과 한라산, 용두암, 성산일출봉 등 다양한 명소가 있습니다.",
    "도쿄": "도쿄는 일본의 수도로, 현대적인 도시와 전통 문화가 공존하며, 쇼핑, 음식, 관광 명소가 풍부합니다.",
    "오사카": "오사카는 일본의 상업 중심지로, 오사카성, 도톤보리, 유니버설 스튜디오 등 다양한 즐길거리가 있는 도시입니다.",
    "파리": "파리는 프랑스의 수도로, 에펠탑, 루브르 박물관, 샹젤리제 거리 등 세계적인 관광명소와 예술 문화를 즐길 수 있는 도시입니다."
}

# -------------------------------
# 날씨 조회
# -------------------------------
def get_weather(lat, lon):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPEN_WEATHER_API_KEY}&units=metric&lang=kr"
        res = requests.get(url)
        data = res.json()
        if res.status_code != 200:
            return None
        return {
            "온도": data["main"]["temp"],
            "체감온도": data["main"]["feels_like"],
            "날씨": data["weather"][0]["description"],
            "습도": data["main"]["humidity"],
            "풍속": data["wind"]["speed"]
        }
    except:
        return None

# -------------------------------
# 지도 생성
# -------------------------------
def create_map(lat, lon, place_name):
    map_ = folium.Map(location=[lat, lon], zoom_start=12)
    folium.Marker([lat, lon], tooltip=place_name).add_to(map_)
    return map_

# -------------------------------
# GPT 일정 생성
# -------------------------------
def generate_itinerary(city, style, days):
    prompt = (
        f"{city} 여행 {days}일 일정, 여행 스타일: {style}로 추천 일정을 만들어주세요. "
        "관광지, 맛집, 카페를 포함하고, 하루 단위로 간단한 설명도 포함해주세요. "
        "출력은 반드시 한국어로 해주세요."
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            max_tokens=1200
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"GPT 일정 생성 실패: {e}"

# -------------------------------
# PDF 생성 (reportlab)
# -------------------------------
def save_pdf(city, style, days, weather, itinerary):
    filename = f"{city}_{style}_{days}일_여행.pdf"
    
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    
    # 기본 내장 한글 폰트
    pdfmetrics.registerFont(TTFont('MalgunGothic', 'C:/Windows/Fonts/malgun.ttf'))
    c.setFont('MalgunGothic', 16)
    c.drawCentredString(width/2, height-2*cm, f"{city} 여행 계획 ({style} 스타일, {days}일)")
    
    c.setFont('MalgunGothic', 12)
    y = height - 3*cm
    
    if weather:
        c.drawString(2*cm, y, f"날씨: {weather['날씨']}, 온도: {weather['온도']}°C, 체감: {weather['체감온도']}°C")
        y -= 0.7*cm
        c.drawString(2*cm, y, f"습도: {weather['습도']}%, 풍속: {weather['풍속']} m/s")
        y -= 1*cm
    
    for line in itinerary.split("\n"):
        c.drawString(2*cm, y, line)
        y -= 0.7*cm
        if y < 2*cm:
            c.showPage()
            c.setFont('MalgunGothic', 12)
            y = height - 2*cm
    
    c.save()
    return filename

# -------------------------------
# Streamlit UI
# -------------------------------
st.title("✈️AI기반 여행 플래너✈️")

city = st.selectbox("여행할 도시 선택", list(CITY_COORDS.keys()))

# 도시 소개
st.subheader(f"🏙 {city} 소개")
st.write(CITY_INTRO[city])

style = st.radio("여행 스타일 선택", ["관광", "맛집", "힐링"])
days = st.number_input("여행 일수", min_value=1, max_value=10, value=3)

lat, lon = CITY_COORDS[city]

st.markdown("---")

# 날씨
st.subheader("🌤 현재 날씨")
weather = get_weather(lat, lon)
if weather:
    st.write(f"**날씨:** {weather['날씨']}")
    st.write(f"**온도:** {weather['온도']}°C")
    st.write(f"**체감온도:** {weather['체감온도']}°C")
    st.write(f"**습도:** {weather['습도']}%")
    st.write(f"**풍속:** {weather['풍속']} m/s")
else:
    st.warning("날씨 정보를 불러올 수 없습니다.")

st.markdown("---")

# 지도
st.subheader("🗺 미니 지도")
my_map = create_map(lat, lon, city)
st_folium(my_map, width=700, height=500)

st.markdown("---")

# GPT 일정
if 'itinerary' not in st.session_state:
    st.session_state.itinerary = ""

st.subheader("📝 GPT 추천 여행 일정")
if st.button("일정 생성"):
    st.session_state.itinerary = generate_itinerary(city, style, days)

st.text_area("추천 일정", value=st.session_state.itinerary, height=400)

# PDF 생성
if st.button("PDF 생성"):
    pdf_file = save_pdf(city, style, days, weather, st.session_state.itinerary)
    st.success("PDF 생성 완료!")
    st.download_button("📄 PDF 다운로드", data=open(pdf_file, "rb").read(), file_name=pdf_file)



