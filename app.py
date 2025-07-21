import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
import os
import google.generativeai as genai

# --- API 키 설정 ---
# Streamlit Secrets에서 API 키를 가져옵니다.
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
except (FileNotFoundError, KeyError):
    GEMINI_API_KEY = "" # 로컬 테스트 시 여기에 API 키를 입력하세요.
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    else:
        st.warning("Gemini API 키가 설정되지 않았습니다. AI 기능을 사용하려면 앱 설정(secrets)에 API 키를 추가해주세요.")

# --- 데이터 로드 함수 ---
@st.cache_data
def load_data(filename):
    """'data' 폴더에서 JSON 파일을 로드합니다."""
    filepath = os.path.join('data', filename)
    if not os.path.exists(filepath):
        st.error(f"'{filepath}' 파일을 찾을 수 없습니다. 'data' 폴더 안에 있는지 확인해주세요.")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"'{filepath}' 파일 로딩 중 오류: {e}")
        return None

# --- Gemini API 호출 함수 ---
def call_gemini(prompt, show_spinner=True):
    """Gemini Pro 모델을 호출하여 텍스트를 생성하는 함수"""
    if not GEMINI_API_KEY:
        return "API 키가 설정되지 않아 AI 기능을 사용할 수 없습니다."
    try:
        model = genai.GenerativeModel('gemini-pro')
        if show_spinner:
            with st.spinner("Gemini AI가 생각 중입니다..."):
                response = model.generate_content(prompt)
                return response.text
        else:
            response = model.generate_content(prompt)
            return response.text
    except Exception as e:
        st.error(f"Gemini API 호출 중 오류가 발생했습니다: {e}")
        return "AI 응답을 생성하는 데 실패했습니다."

# --- 세션 상태 초기화 ---
def initialize_session_state():
    """앱의 모든 단계에서 사용될 변수들을 초기화합니다."""
    defaults = {
        "page": "Start", "project_name": "", "inquiry_question": "",
        "product": "", "process": "", "assessment": "",
        "competencies": "", "achievement_standards": []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- JPG 이미지 생성 함수 (장학자료 양식) ---
def create_lesson_plan_image_table(data):
    """세션 데이터를 바탕으로 '장학 자료' 표 형식의 JPG 이미지를 생성합니다."""
    width, height = 1200, 1600
    margin = 50
    bg_color = (240, 242, 246)
    header_bg_color = (230, 255, 230)
    line_color = (200, 200, 200)

    font_path = os.path.join('data', "Pretendard-Regular.ttf")
    if not os.path.exists(font_path):
        st.error(f"`{font_path}` 파일을 찾을 수 없습니다.")
        return None
    
    try:
        header_font = ImageFont.truetype(font_path, 32)
        body_font = ImageFont.truetype(font_path, 24)
        project_font = ImageFont.truetype(font_path, 36)
    except IOError:
        st.error(f"`{font_path}` 폰트 파일을 열 수 없습니다.")
        return None

    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    def draw_multiline_text_in_box(text, font, box, text_color='black'):
        """지정된 상자 안에 여러 줄의 텍스트를 그립니다."""
        x, y, w, h = box
        lines = []
        for line in text.split('\n'):
            wrapped_lines = textwrap.wrap(line, width=55)
            lines.extend(wrapped_lines if wrapped_lines else [''])
        
        y_text = y + 15
        line_height = font.getbbox("A")[3] + 5
        for line in lines:
            if y_text + line_height < y + h:
                draw.text((x + 15, y_text), line, font=font, fill=text_color)
                y_text += line_height

    # 프로젝트명
    y_pos = margin
    draw.rectangle([(margin, y_pos), (width - margin, y_pos + 80)], fill=header_bg_color, outline=line_color)
    draw_multiline_text_in_box(f"융합 프로젝트명: {data.get('project_name', '')}", project_font, (margin, y_pos, width - margin*2, 80))
    y_pos += 90

    # 테이블 그리기
    rows = {
        "성취기준": "\n".join(data.get('achievement_standards', [])),
        "탐구질문 (또는 핵심아이디어)": data.get('inquiry_question', ''),
        "프로젝트 산출물": data.get('product', ''),
        "프로젝트 과정": data.get('process', ''),
        "과정중심 평가": data.get('assessment', ''),
        "핵심역량, 사회정서역량": data.get('competencies', '')
    }
    
    row_heights = [180, 150, 150, 300, 150, 150]
    header_width = 250

    for i, ((header, content), h) in enumerate(zip(rows.items(), row_heights)):
        # Header Box
        draw.rectangle([(margin, y_pos), (margin + header_width, y_pos + h)], fill=(235, 235, 235), outline=line_color)
        draw_multiline_text_in_box(header, header_font, (margin, y_pos, header_width, h))
        # Content Box
        draw.rectangle([(margin + header_width, y_pos), (width - margin, y_pos + h)], fill='white', outline=line_color)
        draw_multiline_text_in_box(content, body_font, (margin + header_width, y_pos, width - margin*2 - header_width, h))
        y_pos += h

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()

# --- 페이지 렌더링 함수 ---
def render_start_page():
    st.title("GSPBL 수업 설계 내비게이터 🚀 (v2.0)")
    st.markdown("수업 설계를 시작하는 방법을 선택해주세요.")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🌟 수업 예시로 시작하기", use_container_width=True):
            st.session_state.start_method = "example"
    with col2:
        if st.button("💡 교육과정 핵심 아이디어로 시작하기", use_container_width=True):
            st.session_state.start_method = "core_idea"
    with col3:
        if st.button("📄 새로 시작하기", use_container_width=True):
            st.session_state.page = "Design"
            st.rerun()
    
    if "start_method" in st.session_state:
        if st.session_state.start_method == "example":
            janghak_data = load_data("장학자료.json")
            if janghak_data:
                plans = janghak_data["lesson_plans"]
                options = {f"{p['subject']} ({p['grade_group']}): {p['unit']}": p for p in plans}
                selected_plan_title = st.selectbox("불러올 수업 예시를 선택하세요.", options.keys())
                if st.button("이 예시로 설계 시작하기", type="primary"):
                    selected_plan = options[selected_plan_title]
                    st.session_state.project_name = selected_plan.get("unit", "")
                    st.session_state.inquiry_question = selected_plan.get("inquiry_question", "")
                    st.session_state.product = selected_plan.get("evaluation_task", {}).get("product", "")
                    st.session_state.process = "\n".join([f"{item['period']}차시: {item['topic']}" for item in selected_plan.get("teaching_plan", [])])
                    st.session_state.page = "Design"
                    st.rerun()

        elif st.session_state.start_method == "core_idea":
            core_idea_data = load_data("핵심아이디어.json")
            if core_idea_data:
                subjects = sorted(list(set(item["교과"] for item in core_idea_data)))
                selected_subject = st.selectbox("교과를 선택하세요.", subjects)
                
                domains = sorted(list(set(item["영역"] for item in core_idea_data if item["교과"] == selected_subject)))
                selected_domain = st.selectbox("영역을 선택하세요.", domains)

                core_idea = next((item["핵심 아이디어"] for item in core_idea_data if item["교과"] == selected_subject and item["영역"] == selected_domain), "")
                st.info(f"**선택된 핵심 아이디어:**\n\n{core_idea}")

                if st.button("이 아이디어로 설계 시작하기", type="primary"):
                    st.session_state.project_name = f"{selected_subject} ({selected_domain}) 프로젝트"
                    prompt = f"다음 교육과정 핵심 아이디어를 초등학생들이 탐구할 수 있는 GSPBL '도전적인 질문' 1개로 변환해줘. 학생들의 흥미를 유발할 수 있도록 쉽고 재미있는 표현을 사용해줘.\n\n[핵심 아이디어]\n{core_idea}"
                    ai_question = call_gemini(prompt)
                    st.session_state.inquiry_question = ai_question
                    st.session_state.page = "Design"
                    st.rerun()

def render_design_page():
    st.header("✍️ GSPBL 통합 설계 보드")
    
    st.session_state.project_name = st.text_input("융합 프로젝트명", value=st.session_state.project_name)
    
    st.subheader("탐구 질문 (또는 핵심아이디어)")
    inquiry_col1, inquiry_col2 = st.columns([3, 1])
    with inquiry_col1:
        st.session_state.inquiry_question = st.text_area("탐구 질문", value=st.session_state.inquiry_question, height=100, label_visibility="collapsed")
    with inquiry_col2:
        if st.button("🤖 AI로 탐구 질문 생성", use_container_width=True):
            if st.session_state.project_name:
                prompt = f"'{st.session_state.project_name}' 프로젝트에 어울리는 GSPBL '도전적인 질문' 3개를 추천해줘. 번호 없이 한 줄씩."
                suggestions = call_gemini(prompt)
                st.session_state.inquiry_question = suggestions
                st.rerun()
            else:
                st.warning("프로젝트명을 먼저 입력해주세요.")

    st.session_state.product = st.text_input("프로젝트 산출물", value=st.session_state.product)

    st.subheader("프로젝트 과정")
    process_col1, process_col2 = st.columns([3, 1])
    with process_col1:
        st.session_state.process = st.text_area("프로젝트 과정", value=st.session_state.process, height=250, label_visibility="collapsed")
    with process_col2:
        if st.button("🤖 AI로 과정 구체화", use_container_width=True):
            if st.session_state.inquiry_question and st.session_state.process:
                prompt = f"'{st.session_state.inquiry_question}'이라는 탐구 질문으로 진행되는 초등 GSPBL 프로젝트입니다. 아래의 간단한 프로젝트 과정을 구체적인 활동과 디지털 도구 추천을 포함하여 상세하게 다시 작성해주세요.\n\n[기존 과정]\n{st.session_state.process}"
                detailed_process = call_gemini(prompt)
                st.session_state.process = detailed_process
                st.rerun()
            else:
                st.warning("탐구 질문과 간단한 과정을 먼저 입력해주세요.")

    st.session_state.assessment = st.text_area("과정중심 평가 계획", value=st.session_state.assessment, height=150)
    st.session_state.competencies = st.text_input("핵심역량, 사회정서역량", value=st.session_state.competencies)

    st.markdown("---")
    st.header("✨ 최종 설계도 생성 및 저장")
    
    final_data = {key: st.session_state[key] for key in st.session_state}
    image_data = create_lesson_plan_image_table(final_data)
    if image_data:
        st.download_button(label="🖼️ 수업 설계 요약표 JPG로 저장", data=image_data, file_name=f"GSPBL_설계요약표.jpg", mime="image/jpeg")

    if st.button("↩️ 처음으로 돌아가기"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        initialize_session_state()
        st.rerun()


# --- 메인 앱 로직 ---
def main():
    st.set_page_config(page_title="GSPBL 내비게이터", layout="wide")
    initialize_session_state()

    if st.session_state.page == "Start":
        render_start_page()
    elif st.session_state.page == "Design":
        render_design_page()

    footer_css = """
    <style>
    .footer { position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: transparent; color: #808080;
        text-align: center; padding: 10px; font-size: 16px; }
    </style>
    <div class="footer"><p>서울가동초 백인규</p></div>
    """
    st.markdown(footer_css, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
