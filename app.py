import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
import os
import google.generativeai as genai

# --- API 키 설정 ---
# Streamlit Secrets에서 API 키를 가져옵니다.
# 로컬에서 테스트할 경우, 직접 키를 입력하거나 환경 변수를 사용하세요.
try:
    # For Streamlit Community Cloud, set API key in st.secrets
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
except (FileNotFoundError, KeyError):
    # Local development
    # 로컬에서 실행 시, 여기에 직접 API 키를 입력하세요.
    # 예: GEMINI_API_KEY = "YOUR_API_KEY_HERE"
    # 실제 배포 시에는 이 부분을 비워두거나 st.secrets를 사용하는 것이 안전합니다.
    GEMINI_API_KEY = "" 
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    else:
        # API 키가 없을 경우 경고 메시지를 표시하고 AI 기능을 비활성화합니다.
        st.warning("Gemini API 키가 설정되지 않았습니다. AI 기능을 사용하려면 API 키를 입력해주세요.")


# --- Gemini API 호출 함수 ---
def call_gemini(prompt):
    """Gemini Pro 모델을 호출하여 텍스트를 생성하는 함수"""
    if not GEMINI_API_KEY:
        return "API 키가 설정되지 않아 AI 기능을 사용할 수 없습니다."
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Gemini API 호출 중 오류가 발생했습니다: {e}")
        return "AI 응답을 생성하는 데 실패했습니다."

# --- 데이터 로드 함수 ---
@st.cache_data
def load_achievement_data(grade_group):
    """학년군에 맞는 성취기준 JSON 파일을 로드합니다."""
    file_map = {
        '1-2학년군': '1-2학년군_성취수준.json',
        '3-4학년군': '3-4학년군_성취수준.json',
        '5-6학년군': '5-6학년군_성취수준.json'
    }
    filename = file_map.get(grade_group)
    if not filename or not os.path.exists(filename):
        st.error(f"'{filename}' 파일을 찾을 수 없습니다. `app.py`와 같은 폴더에 있는지 확인해주세요.")
        return None
    try:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            if content.startswith('\ufeff'):
                content = content[1:]
            data = json.loads(content)
            return data.get('content', data)
    except json.JSONDecodeError as e:
        st.error(f"'{filename}' 파일 파싱 중 오류가 발생했습니다: {e}")
        return None

# --- 세션 상태 초기화 ---
def initialize_session_state():
    """앱의 모든 단계에서 사용될 변수들을 초기화합니다."""
    defaults = {
        "page": "STEP 1",
        "project_theme": "",
        "public_product": "",
        "selected_standards_dict": {},
        "selected_competencies": [],
        "inquiry_plan": "",
        "student_choice": [],
        "revision_plan": "",
        "reflection_plan": "",
        "ai_suggestions": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- 페이지 이동 함수 ---
def next_page(page_name):
    st.session_state.page = page_name

# --- JPG 이미지 생성 함수 ---
def create_lesson_plan_image(data):
    """세션 데이터를 바탕으로 JPG 이미지를 생성합니다."""
    width, height = 1200, 2200
    margin = 60
    font_path = "font.ttf"
    if not os.path.exists(font_path):
        st.error(f"`{font_path}` 파일을 찾을 수 없습니다.")
        return None
    try:
        title_font = ImageFont.truetype(font_path, 50)
        header_font = ImageFont.truetype(font_path, 35)
        body_font = ImageFont.truetype(font_path, 24)
    except IOError:
        st.error(f"`{font_path}` 폰트 파일을 열 수 없습니다.")
        return None

    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    y_position = margin

    def draw_multiline_text(text, font, text_color, start_y, indent=0):
        lines = []
        for line in text.split('\n'):
            wrapped_lines = textwrap.wrap(line, width=70)
            lines.extend(wrapped_lines if wrapped_lines else [''])
        line_height = font.getbbox("A")[3] + 8
        x = margin + indent
        for line in lines:
            if start_y < height - margin:
                draw.text((x, start_y), line, font=font, fill=text_color)
                start_y += line_height
        return start_y

    title_text = f'"{data["project_theme"]}" GSPBL 수업 설계도'
    y_position = draw_multiline_text(title_text, title_font, 'black', y_position)
    y_position += 30
    draw.line([(margin, y_position), (width - margin, y_position)], fill="gray", width=2)
    y_position += 30
    
    sections = {
        "최종 결과물 공개": data["public_product"],
        "연결된 성취기준": '\n'.join(data["selected_standards_dict"].values()) if data["selected_standards_dict"] else "선택된 성취기준이 없습니다.",
        "핵심 성공 역량": ', '.join(data["selected_competencies"]) if data["selected_competencies"] else "선택된 역량이 없습니다.",
        "지속적 탐구 계획": data["inquiry_plan"],
        "학생 선택권": ', '.join(data["student_choice"]),
        "비평 및 개선 계획": data["revision_plan"],
        "성찰 계획": data["reflection_plan"]
    }

    for header, content in sections.items():
        if y_position > height - 150: break
        draw.text((margin, y_position), f"■ {header}", font=header_font, fill='#003366')
        y_position += 50
        y_position = draw_multiline_text(content, body_font, 'black', y_position, indent=20)
        y_position += 40

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


# --- 각 페이지 렌더링 함수 ---
def render_step1():
    st.header("🗺️ STEP 1: 프로젝트 주제 정하기 (AI 도움받기)")
    
    # --- AI로 주제 추천받기 ---
    st.subheader("🤖 AI로 도전적인 질문 추천받기")
    ai_keyword = st.text_input("프로젝트 관련 키워드를 입력하세요 (예: 환경, 우리 동네, 건강)", key="ai_keyword")
    if st.button("AI에게 질문 아이디어 요청하기"):
        if ai_keyword:
            prompt = f"초등학생 대상 GSPBL 프로젝트 수업에 사용할 '도전적인 질문' 아이디어를 '{ai_keyword}'라는 키워드를 중심으로 5개만 생성해줘. 각 아이디어는 물음표로 끝나는 질문 형태로, 한 문장으로 간결하게 만들어줘. 답변은 번호 없이, 각 질문을 한 줄씩 나열해줘."
            with st.spinner("Gemini AI가 창의적인 질문을 생성 중입니다..."):
                response = call_gemini(prompt)
                st.session_state.ai_suggestions = [line.strip() for line in response.split('\n') if line.strip()]
        else:
            st.warning("추천을 받으려면 키워드를 입력해주세요.")

    if st.session_state.ai_suggestions:
        st.write("AI가 추천하는 질문 아이디어입니다. 마음에 드는 질문을 클릭하면 아래에 자동으로 입력됩니다.")
        for suggestion in st.session_state.ai_suggestions:
            if st.button(suggestion, key=suggestion):
                st.session_state.project_theme = suggestion
                st.rerun() # 클릭 시 바로 반영되도록

    st.markdown("---")
    
    # --- 수동 입력 ---
    st.subheader("📝 프로젝트 기본 정보 입력")
    st.session_state.project_theme = st.text_input("**프로젝트 대주제 (핵심 질문)**", value=st.session_state.project_theme, placeholder="예: 우리 학교 급식실은 왜 항상 시끄러울까?")
    st.session_state.public_product = st.text_area("**최종 결과물 공개 계획**", value=st.session_state.public_product, placeholder="예: 학부모님을 초청하여 '급식실 소음 줄이기' 캠페인 결과 발표회를 연다.")
    
    if st.button("다음 단계로", type="primary"):
        next_page("STEP 2")
        st.rerun()

def render_step2():
    st.header("🚗 STEP 2: 탐구 여정 디자인하기 (AI 도움받기)")

    # --- 지속적 탐구 (AI 기능 포함) ---
    st.subheader("1. 지속적 탐구 (Sustained Inquiry)")
    inquiry_examples = ["문제 발견 및 질문 만들기", "실태 조사 (설문, 관찰)", "전문가 인터뷰", "자료 및 문헌 조사", "해결 방안 브레인스토밍", "캠페인/시제품 기획", "산출물 제작", "수정 및 보완"]
    st.multiselect("예시 활동을 선택하여 계획의 뼈대를 만들어보세요.", inquiry_examples, key="ms_inquiry_plan")
    
    current_plan = st.session_state.inquiry_plan
    if not current_plan and st.session_state.ms_inquiry_plan:
        current_plan = "\n".join([f"- {ex}" for ex in st.session_state.ms_inquiry_plan])

    st.session_state.inquiry_plan = st.text_area("탐구 활동 계획을 간단히 작성하거나, AI의 도움을 받아 구체화하세요.", value=current_plan, height=200, key="ta_inquiry_plan")

    if st.button("🤖 AI로 탐구 활동 구체화하기"):
        if st.session_state.project_theme and st.session_state.inquiry_plan:
            prompt = f"'{st.session_state.project_theme}'라는 주제의 초등학생 GSPBL 프로젝트가 있습니다. 아래의 간단한 탐구 활동 계획을 학생들이 실제로 수행할 수 있도록 구체적이고 창의적인 세부 활동으로 확장해주세요. 각 단계별로 어떤 디지털 도구(예: Padlet, Canva, Flip)를 활용할 수 있는지도 추천해주세요.\n\n[기존 계획]\n{st.session_state.inquiry_plan}"
            with st.spinner("Gemini AI가 활동 계획을 상세하게 만들고 있습니다..."):
                detailed_plan = call_gemini(prompt)
                st.session_state.inquiry_plan = detailed_plan
                st.rerun()
        else:
            st.warning("AI의 도움을 받으려면 STEP 1의 '프로젝트 대주제'와 '탐구 활동 계획'을 먼저 입력해주세요.")

    # --- 나머지 계획들 ---
    st.subheader("2. 학생 의사 & 선택권 (Student Voice & Choice)")
    st.session_state.student_choice = st.multiselect("학생들에게 어떤 선택권을 줄 수 있을까요?", options=["모둠 구성 방식", "자료 수집 방법", "산출물 형태", "역할 분담", "발표 방식"], default=st.session_state.student_choice)
    
    st.subheader("3. 비평과 개선 (Critique and Revision)")
    st.session_state.revision_plan = st.text_area("피드백 및 개선 계획을 작성해주세요.", value=st.session_state.revision_plan, height=150, placeholder="예: 중간 발표회를 열어 동료들에게 '좋았던 점/개선할 점' 스티커 피드백을 받는다.")
    
    st.subheader("4. 성찰 (Reflection)")
    st.session_state.reflection_plan = st.text_area("성찰 활동 계획을 작성해주세요.", value=st.session_state.reflection_plan, height=150, placeholder="예: 매일 활동 종료 5분 전, 구글 문서에 '오늘의 한 줄 학습 일기'를 작성하게 한다.")

    st.markdown("---")
    st.header("✨ 최종 설계도 생성")
    
    # 최종 설계도 표시 및 다운로드
    final_data = {key: st.session_state[key] for key in st.session_state}
    image_data = create_lesson_plan_image(final_data)
    if image_data:
        st.download_button(label="🖼️ JPG로 다운로드", data=image_data, file_name=f"GSPBL_설계도.jpg", mime="image/jpeg")

    if st.button("이전 단계로"):
        next_page("STEP 1")
        st.rerun()

# --- 메인 앱 로직 ---
def main():
    st.set_page_config(page_title="GSPBL 내비게이터", layout="wide")
    st.title("GSPBL 수업 설계 내비게이터 🚀 (AI 버전)")
    
    initialize_session_state()

    page_map = {
        "STEP 1": render_step1,
        "STEP 2": render_step2,
    }
    page_map[st.session_state.page]()

    footer_css = """
    <style>
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: transparent; color: #808080;
        text-align: center; padding: 10px; font-size: 16px;
    }
    </style>
    <div class="footer"><p>서울가동초 백인규</p></div>
    """
    st.markdown(footer_css, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
