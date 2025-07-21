import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
import os
import google.generativeai as genai
import re

# --- 1. 초기 설정 및 API 키 구성 ---
st.set_page_config(
    page_title="GSPBL 수업 설계 내비게이터",
    page_icon="🚀",
    layout="centered",
    initial_sidebar_state="auto",
)

# Gemini API 키 설정 (보안 강화)
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except (FileNotFoundError, KeyError):
    GEMINI_API_KEY = ""  # 로컬 테스트 시 여기에 키 입력

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"API 키 설정 중 오류가 발생했습니다: {e}")
else:
    st.warning("Gemini API 키가 설정되지 않았습니다. AI 제안 기능을 사용하려면 앱 설정(Secrets)에 키를 추가하거나 코드에 직접 입력해주세요.")


# --- 2. 데이터 로드 및 처리 함수 ---

@st.cache_data
def load_json_data(filename):
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

@st.cache_data
def parse_achievement_standards(grade_group):
    """
    성취기준 JSON 파일에서 교과 및 성취기준을 파싱합니다.
    """
    filename_map = {
        "1-2학년군": "1-2학년군_성취수준.json",
        "3-4학년군": "3-4학년군_성취수준.json",
        "5-6학년군": "5-6학년군_성취수준.json",
    }
    filename = filename_map.get(grade_group)
    if not filename:
        return {}

    data = load_json_data(filename)
    if not data or "content" not in data:
        return {}

    text = data["content"]
    subjects = {}
    
    # 교과 목록을 찾는 더 안정적인 정규식으로 수정
    subject_matches = re.finditer(r'\n(\d+)\.\s+([가-힣]+(?:\s*생활)?)\n', text)
    subject_list = [(m.group(2).strip(), m.start()) for m in subject_matches]
    
    for i, (subject_name, start_index) in enumerate(subject_list):
        end_index = subject_list[i+1][1] if i + 1 < len(subject_list) else len(text)
        subject_text = text[start_index:end_index]
        
        standards = re.findall(r'(\[\d{1,2}[가-힣]{1,2}\d{2}-\d{2}\])([^\[]+)', subject_text)
        
        if standards:
            subjects[subject_name] = {f"{code} {desc.strip()}": f"{code} {desc.strip()}" for code, desc in standards}

    return subjects


# --- 3. AI 및 이미지 생성 함수 ---

def call_gemini(prompt, show_spinner=True):
    """Gemini 모델을 호출하여 텍스트를 생성합니다."""
    if not GEMINI_API_KEY:
        return "⚠️ AI 기능 비활성화: Gemini API 키가 설정되지 않았습니다."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        if show_spinner:
            with st.spinner("🚀 Gemini AI가 선생님의 아이디어를 확장하고 있어요..."):
                response = model.generate_content(prompt)
                return response.text
        else:
            response = model.generate_content(prompt)
            return response.text
    except Exception as e:
        return f"AI 응답 생성에 실패했습니다. API 키가 유효한지 확인해주세요. 오류: {e}"

def create_lesson_plan_images():
    """세션 데이터를 바탕으로 2페이지 분량의 '수업 설계도' JPG 이미지를 생성합니다."""
    data = st.session_state
    
    rows_page1 = {
        "🎯 프로젝트 대주제 (도전적 질문)": data.get('project_title', ''),
        "📢 최종 결과물 공개": data.get('public_product', ''),
        "📚 교과 성취기준": "\n".join(data.get('selected_standards', [])),
        "💡 핵심역량": "\n".join(f"• {c}" for c in data.get('selected_core_competencies', [])),
        "🌱 사회정서 역량": "\n".join(f"• {c}" for c in data.get('selected_sel_competencies', [])),
    }
    
    rows_page2 = {
        "🧭 지속적 탐구": data.get('sustained_inquiry', ''),
        "📈 과정중심 평가": data.get('process_assessment', ''),
        "🗣️ 학생의 의사 & 선택권": "\n".join(data.get('student_voice_choice', [])),
        "🔄 비평과 개선": data.get('critique_revision', ''),
        "🤔 성찰": data.get('reflection', '')
    }

    images = []
    for page_num, rows in enumerate([rows_page1, rows_page2], 1):
        width, height = 1200, 1700
        margin = 50
        bg_color = (255, 255, 255)
        header_bg_color = (230, 245, 255)
        line_color = (200, 200, 200)

        font_path = os.path.join('data', "Pretendard-Regular.ttf")
        if not os.path.exists(font_path):
            st.error(f"`{font_path}` 폰트 파일을 찾을 수 없습니다.")
            return []
        
        try:
            title_font = ImageFont.truetype(font_path, 40)
            header_font = ImageFont.truetype(font_path, 28)
            body_font = ImageFont.truetype(font_path, 22)
        except IOError:
            st.error(f"`{font_path}` 폰트 파일을 열 수 없습니다.")
            return []

        img = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)

        def draw_multiline_text_in_box(text, font, box, text_color='black', h_align='left', v_align='top'):
            x, y, w, h = box
            lines = []
            for line in text.split('\n'):
                wrapped_lines = textwrap.wrap(line, width=int(w / (font.size * 0.55)), break_long_words=True)
                lines.extend(wrapped_lines if wrapped_lines else [''])
            
            line_height = font.getbbox("A")[3] + 6
            total_text_height = len(lines) * line_height
            
            y_text = y + 15
            if v_align == 'center':
                y_text = y + (h - total_text_height) / 2
            
            for line in lines:
                line_width = draw.textlength(line, font=font)
                x_text = x + 15
                if h_align == 'center':
                    x_text = x + (w - line_width) / 2
                
                if y_text + line_height < y + h + 15:
                    draw.text((x_text, y_text), line, font=font, fill=text_color)
                    y_text += line_height
        
        y_pos = margin
        draw.rectangle([(margin, y_pos), (width - margin, y_pos + 80)], fill=header_bg_color, outline=line_color)
        draw_multiline_text_in_box(f"GSPBL 수업 설계도 ({page_num}/2)", title_font, (margin, y_pos, width - margin*2, 80), h_align='center', v_align='center')
        y_pos += 80 + 10

        for header, content in rows.items():
            lines = []
            for line in content.split('\n'):
                wrapped_lines = textwrap.wrap(line, width=65)
                lines.extend(wrapped_lines if wrapped_lines else [''])
            row_height = max(100, len(lines) * 30 + 40)
            
            if y_pos + row_height > height - margin: # 페이지 넘어가지 않게 방지
                row_height = height - margin - y_pos

            draw.rectangle([(margin, y_pos), (margin + 300, y_pos + row_height)], fill=(245, 245, 245), outline=line_color)
            draw_multiline_text_in_box(header, header_font, (margin, y_pos, 300, row_height), v_align='center')
            draw.rectangle([(margin + 300, y_pos), (width - margin, y_pos + row_height)], fill='white', outline=line_color)
            draw_multiline_text_in_box(content, body_font, (margin + 300, y_pos, width - margin*2 - 300, row_height))
            y_pos += row_height

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        images.append(buffer.getvalue())
        
    return images


# --- 4. 세션 상태 초기화 ---

def initialize_session_state():
    """앱의 모든 단계에서 사용될 변수들을 초기화합니다."""
    if "page" not in st.session_state:
        st.session_state.page = 0

    defaults = {
        "project_title": "", "public_product": "",
        "grade_group": "5-6학년군", "selected_subject": None,
        "selected_standards": [], 
        "selected_core_competencies": [], "selected_sel_competencies": [],
        "sustained_inquiry": "", "student_voice_choice": [],
        "critique_revision": "", "reflection": "", "process_assessment": "",
        "ai_feedback": "",
        "start_method": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- 5. 페이지 렌더링 함수 ---

def render_start_page():
    st.title("GSPBL 수업 설계 내비게이터 🚀")
    st.markdown("---")
    st.subheader("수업 설계를 시작하는 방법을 선택해주세요.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💡 교육과정 핵심 아이디어로 시작하기", use_container_width=True):
            st.session_state.start_method = "core_idea"
            st.rerun()
    with col2:
        if st.button("✍️ 새로 시작하기", use_container_width=True):
            st.session_state.page = 1
            st.rerun()

    if st.session_state.start_method == "core_idea":
        st.markdown("---")
        st.subheader("핵심 아이디어 선택")
        core_idea_data = load_json_data("핵심아이디어.json")
        if core_idea_data:
            subjects = sorted(list(set(item["교과"] for item in core_idea_data)))
            selected_subject = st.selectbox("교과를 선택하세요.", subjects)
            
            domains = sorted(list(set(item["영역"] for item in core_idea_data if item["교과"] == selected_subject)))
            selected_domain = st.selectbox("영역을 선택하세요.", domains)

            core_idea = next((item["핵심 아이디어"] for item in core_idea_data if item["교과"] == selected_subject and item["영역"] == selected_domain), "")
            
            with st.container(border=True):
                st.write("**선택된 핵심 아이디어**")
                st.info(core_idea)

            if st.button("이 아이디어로 설계 시작하기", type="primary", use_container_width=True):
                prompt = f"다음 교육과정 핵심 아이디어를 초등학생들이 탐구할 수 있는 GSPBL '도전적인 질문' 1개로 변환해줘. 학생들의 흥미를 유발할 수 있도록 쉽고 재미있는 표현을 사용해줘.\n\n[핵심 아이디어]\n{core_idea}"
                ai_question = call_gemini(prompt)
                st.session_state.project_title = ai_question.strip().replace('"', '').replace('*', '')
                st.session_state.page = 1
                st.rerun()

def render_step1():
    st.header("🗺️ STEP 1. 최종 목적지 설정하기")
    st.caption("프로젝트의 대주제와 최종 결과물을 설정하여 전체적인 방향을 정의합니다.")
    
    st.subheader("프로젝트 대주제 (Challenging Problem or Question)")
    st.session_state.project_title = st.text_area(
        "프로젝트를 관통하는 핵심 질문을 입력하세요.",
        value=st.session_state.project_title,
        placeholder="예: 우리 학교 급식실은 왜 항상 시끄러울까?",
        height=150,
        label_visibility="collapsed"
    )
    st.info("💡 **팁:** 학생의 삶과 연결되고, 정답이 하나가 아닌 질문을 만들어 보세요.")

    with st.expander("🤖 AI로 '도전적인 질문' 아이디어 얻기"):
        ai_keyword = st.text_input("프로젝트 관련 핵심 키워드를 입력해보세요.", placeholder="예: 기후 위기, 우리 동네 문제, 재활용")
        if st.button("AI 제안 받기"):
            if ai_keyword:
                prompt = f"초등학생 대상 GSPBL 프로젝트를 위한 '도전적인 질문'을 생성해줘. 핵심 키워드는 '{ai_keyword}'야. 학생들이 흥미를 느끼고 깊이 탐구하고 싶게 만드는, 정답이 없는 질문 5개를 제안해줘. 번호 없이 한 줄씩만."
                suggestions = call_gemini(prompt)
                st.session_state.project_title = suggestions
                st.rerun()
            else:
                st.warning("키워드를 먼저 입력해주세요.")

    st.subheader("최종 결과물 공개 (Public Product)")
    st.session_state.public_product = st.text_area(
        "학생들의 결과물을 누구에게, 어떻게 공개할지 구체적으로 작성하세요.",
        value=st.session_state.public_product,
        placeholder="예: 학부모님을 초청하여 '급식실 소음 줄이기' 캠페인 결과 발표회를 연다.",
        height=150,
        label_visibility="collapsed"
    )
    st.info("💡 **팁:** 결과물이 교실 밖으로 공개될 때, 학생들은 진짜 세상의 문제를 해결하고 있다는 책임감과 자부심을 느낍니다.")

    with st.expander("🤖 AI로 '최종 산출물' 아이디어 얻기"):
        if st.button("AI 제안 받기", key="product_ai"):
            if st.session_state.project_title:
                prompt = f"초등학생 대상 GSPBL 프로젝트를 위한 '최종 결과물 공개(Public Product)' 아이디어를 5가지 제안해줘. 이 프로젝트의 도전적 질문은 '{st.session_state.project_title}'이야. 학생들이 프로젝트 결과를 교실 밖 실제 세상과 공유할 수 있는 구체적이고 의미 있는 방법을 제안해줘. 번호 없이 한 줄씩만."
                suggestions = call_gemini(prompt)
                st.session_state.public_product = suggestions
                st.rerun()
            else:
                st.warning("프로젝트 대주제를 먼저 입력해주세요.")

def render_step2():
    st.header("🧭 STEP 2. 학습 나침반 준비하기")
    st.caption("프로젝트를 통해 달성할 교과 성취기준과 핵심 역량을 명확히 설정합니다.")

    st.subheader("교과 성취기준 연결")
    
    grade_group = st.radio(
        "학년군 선택",
        ["1-2학년군", "3-4학년군", "5-6학년군"],
        index=["1-2학년군", "3-4학년군", "5-6학년군"].index(st.session_state.grade_group),
        horizontal=True,
        key="grade_group"
    )

    achievement_data = parse_achievement_standards(grade_group)
    
    if not achievement_data:
        st.warning(f"'{grade_group}'의 성취기준 데이터를 불러오는 데 실패했습니다. 'data' 폴더의 JSON 파일을 확인해주세요.")
    else:
        subjects = list(achievement_data.keys())
        selected_subject = st.selectbox("교과 선택", options=subjects)

        if selected_subject:
            standards = achievement_data[selected_subject]
            st.session_state.selected_standards = st.multiselect(
                "프로젝트와 관련된 성취기준을 모두 선택하세요.",
                options=list(standards.values()),
                default=st.session_state.selected_standards
            )

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💡 핵심역량")
        core_competencies = {
            "자기관리 역량": "자아정체성과 자신감을 가지고 자신의 삶과 진로에 필요한 기초 능력과 자질을 갖추어 자기주도적으로 살아가는 능력",
            "지식정보처리 역량": "문제를 합리적으로 해결하기 위해 다양한 영역의 지식과 정보를 처리하고 활용하는 능력",
            "창의적 사고 역량": "폭넓은 기초 지식을 바탕으로 다양한 전문 분야의 지식, 기술, 경험을 융합적으로 활용하여 새로운 것을 창출하는 능력",
            "심미적 감성 역량": "인간에 대한 공감적 이해와 문화적 감수성을 바탕으로 삶의 의미와 가치를 발견하고 향유하는 능력",
            "협력적 소통 역량": "다양한 상황에서 자신의 생각과 감정을 효과적으로 표현하고 다른 사람의 의견을 경청하며 존중하는 태도로 협력하는 능력",
            "공동체 역량": "지역ㆍ국가ㆍ세계 공동체의 구성원에게 요구되는 가치와 태도를 가지고 공동체 발전에 적극적으로 참여하는 능력"
        }
        selected_core = []
        for comp, desc in core_competencies.items():
            if st.checkbox(comp, value=comp in st.session_state.selected_core_competencies, key=f"core_{comp}"):
                st.caption(f" L {desc}")
                selected_core.append(comp)
        st.session_state.selected_core_competencies = selected_core

    with col2:
        st.subheader("🌱 사회정서 역량")
        sel_competencies = {
            "자기 인식 역량": "자신의 감정, 생각, 가치를 정확하게 인식하고, 자신의 강점과 한계를 이해하는 능력입니다.",
            "자기 관리 역량": "자신의 감정, 생각, 행동을 효과적으로 조절하고 스트레스 관리, 자기 동기 부여, 목표 설정을 통해 과제를 성취하는 능력입니다.",
            "사회적 인식 역량": "타인의 감정과 관점을 이해하고 공감하며, 집단과 공동체 내의 긍정적 규범을 이해하는 능력입니다.",
            "관계 기술 역량": "명확한 의사소통, 적극적인 경청, 협력, 갈등 해결 등을 통해 타인과 긍정적인 관계를 형성하고 유지하는 능력입니다.",
            "책임 있는 의사결정 역량": "윤리적 기준, 사회적 규범, 안전 문제 등을 고려하여 자신과 타인에 대해 건설적인 선택을 하는 능력입니다."
        }
        selected_sel = []
        for comp, desc in sel_competencies.items():
            if st.checkbox(comp, value=comp in st.session_state.selected_sel_competencies, key=f"sel_{comp}"):
                st.caption(f" L {desc}")
                selected_sel.append(comp)
        st.session_state.selected_sel_competencies = selected_sel


def render_step3():
    st.header("🚗 STEP 3. 탐구 여정 디자인하기")
    st.caption("학생들이 경험할 구체적인 탐구, 피드백, 성찰 활동을 계획합니다.")

    st.subheader("지속적 탐구 (Sustained Inquiry)")
    st.markdown("학생들은 어떤 과정을 통해 깊이 있는 탐구를 진행하게 될까요?")
    with st.expander("🤖 AI로 '지속적 탐구' 과정 제안받기", expanded=True):
        inquiry_tags = [
            "문제 발견 단계", "질문 만들기", "실태 조사 (설문, 관찰)", 
            "전문가 인터뷰", "자료 및 문헌 조사", "해결 방안 탐색",
            "시제품/캠페인 기획", "산출물 제작", "수정 및 보완"
        ]
        selected_tags = st.multiselect("주요 활동을 선택하여 탐구의 뼈대를 만들어보세요.", options=inquiry_tags)
        
        if st.button("선택한 활동으로 AI 과정 구체화하기"):
            if selected_tags and st.session_state.project_title:
                prompt = (f"초등학생 대상 GSPBL 프로젝트의 '지속적 탐구' 과정을 구체적으로 설계해줘.\n"
                          f"프로젝트의 도전적 질문은 '{st.session_state.project_title}'이야.\n"
                          f"다음과 같은 활동들을 포함해서, 각 단계별로 학생들이 무엇을 할지, 어떤 디지털 도구를 사용하면 좋을지 예시를 들어 상세한 과정안을 작성해줘.\n\n"
                          f"포함할 활동: {', '.join(selected_tags)}")
                detailed_process = call_gemini(prompt)
                st.session_state.sustained_inquiry = detailed_process
            else:
                st.warning("프로젝트 대주제와 주요 활동을 먼저 입력/선택해주세요.")

    st.session_state.sustained_inquiry = st.text_area(
        "탐구 과정을 구체적으로 작성하거나 AI 제안을 수정하세요.",
        value=st.session_state.sustained_inquiry,
        height=250,
        label_visibility="collapsed"
    )

    st.subheader("과정중심 평가 (Process-based Assessment)")
    st.markdown("탐구 과정 속에서 학생의 학습과 성장을 어떻게 확인하고 지원할까요?")
    if st.button("🤖 AI로 평가 방법 제안받기", key="assessment_ai"):
        if st.session_state.project_title and st.session_state.sustained_inquiry:
            prompt = (f"초등학생 대상 GSPBL 프로젝트를 위한 '과정중심 평가' 방법을 5가지 제안해줘.\n"
                      f"프로젝트 주제: '{st.session_state.project_title}'\n"
                      f"주요 탐구 과정:\n{st.session_state.sustained_inquiry}\n\n"
                      f"위 내용에 가장 적합한 평가 방법을 구체적인 예시와 함께 제안해줘. 예를 들어 '체크리스트'라면 어떤 항목을 넣을지, '동료평가'라면 어떤 질문을 할지 등을 포함해줘. 번호 없이 한 줄씩만.")
            suggestions = call_gemini(prompt)
            st.session_state.process_assessment = suggestions
        else:
            st.warning("프로젝트 대주제와 지속적 탐구 계획을 먼저 입력해주세요.")

    st.session_state.process_assessment = st.text_area(
        "과정중심 평가 계획",
        value=st.session_state.process_assessment,
        placeholder="AI 제안을 받거나 직접 입력하세요. 예: 자기평가 체크리스트, 동료 상호평가, 교사 관찰 기록 등",
        height=150, label_visibility="collapsed"
    )

    st.subheader("학생의 의사 & 선택권 (Student Voice and Choice)")
    st.markdown("학생들이 '디자이너'로서 프로젝트에 참여하도록 어떤 선택권을 줄 수 있을까요?")
    voice_options = {
        "모둠 구성 방식": False, "자료 수집 방법": False, 
        "산출물 형태 (영상, 포스터 등)": False, "역할 분담": False, "발표 방식": False
    }
    selected_voice = []
    for option, default_val in voice_options.items():
        if st.checkbox(option, value=option in st.session_state.student_voice_choice):
            selected_voice.append(option)
    st.session_state.student_voice_choice = selected_voice

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("비평과 개선 (Critique & Revision)")
        st.markdown("어떻게 피드백을 받고 결과물을 발전시킬까요?")
        if st.button("🤖 AI로 비평/개선 방법 제안받기", key="critique_ai"):
             if st.session_state.project_title:
                prompt = f"초등학생 대상 GSPBL 프로젝트를 위한 '비평과 개선(Critique & Revision)' 활동 아이디어를 5가지 제안해줘. 이 프로젝트의 주제는 '{st.session_state.project_title}'이고, 최종 결과물은 '{st.session_state.public_product}'이야. 학생들이 서로 의미 있는 피드백을 주고받고, 자신의 결과물을 발전시킬 수 있는 구체적이고 창의적인 방법을 제안해줘. 번호 없이 한 줄씩만."
                suggestions = call_gemini(prompt)
                st.session_state.critique_revision = suggestions
             else:
                st.warning("STEP 1의 프로젝트 대주제를 먼저 입력해주세요.")
        
        st.session_state.critique_revision = st.text_area(
            "피드백 계획",
            value=st.session_state.critique_revision,
            placeholder="AI 제안을 받거나 직접 입력하세요.",
            height=200, label_visibility="collapsed"
        )
    with col2:
        st.subheader("성찰 (Reflection)")
        st.markdown("배움과 성장을 어떻게 돌아보게 할까요?")
        if st.button("🤖 AI로 성찰 방법 제안받기", key="reflection_ai"):
            if st.session_state.project_title:
                prompt = f"초등학생 대상 GSPBL 프로젝트를 위한 '성찰(Reflection)' 활동 아이디어를 5가지 제안해줘. 이 프로젝트의 주제는 '{st.session_state.project_title}'이야. 학생들이 프로젝트 과정 전반에 걸쳐 자신의 학습, 성장, 느낀 점을 의미 있게 돌아볼 수 있는 구체적이고 창의적인 방법을 제안해줘. 번호 없이 한 줄씩만."
                suggestions = call_gemini(prompt)
                st.session_state.reflection = suggestions
            else:
                st.warning("STEP 1의 프로젝트 대주제를 먼저 입력해주세요.")

        st.session_state.reflection = st.text_area(
            "성찰 계획",
            value=st.session_state.reflection,
            placeholder="AI 제안을 받거나 직접 입력하세요.",
            height=200, label_visibility="collapsed"
        )

def render_step4():
    st.header("✨ STEP 4. 최종 설계도 확인 및 내보내기")
    st.caption("입력된 모든 내용을 하나의 문서로 통합하여 확인하고, 저장 및 공유할 수 있습니다.")
    st.markdown("---")

    final_data = {
        "🎯 프로젝트 대주제": "project_title",
        "📢 최종 결과물 공개": "public_product",
        "📚 교과 성취기준": "selected_standards",
        "💡 핵심역량": "selected_core_competencies",
        "🌱 사회정서 역량": "selected_sel_competencies",
        "🧭 지속적 탐구": "sustained_inquiry",
        "📈 과정중심 평가": "process_assessment",
        "🗣️ 학생의 의사 & 선택권": "student_voice_choice",
        "🔄 비평과 개선": "critique_revision",
        "🤔 성찰": "reflection"
    }

    for title, key in final_data.items():
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.subheader(title)
                content = st.session_state.get(key, "")
                if isinstance(content, list):
                    st.write("\n".join(f"- {item}" for item in content) if content else "입력된 내용이 없습니다.")
                else:
                    st.write(content if content else "입력된 내용이 없습니다.")
            with col2:
                if st.button(f"✏️ 수정", key=f"edit_{key}", use_container_width=True):
                    if key in ["project_title", "public_product"]:
                        st.session_state.page = 1
                    elif key in ["selected_standards", "selected_core_competencies", "selected_sel_competencies"]:
                        st.session_state.page = 2
                    else:
                        st.session_state.page = 3
                    st.rerun()

    st.markdown("---")
    
    with st.expander("🤖 AI에게 수업 설계안 종합 피드백 받기"):
        if st.button("피드백 요청하기", use_container_width=True):
            full_plan = ""
            for title, key in final_data.items():
                content = st.session_state.get(key, "")
                content_str = "\n".join(content) if isinstance(content, list) else content
                full_plan += f"### {title}\n{content_str}\n\n"
            
            prompt = (f"당신은 GSPBL(Gold Standard Project Based Learning) 전문가입니다.\n"
                      f"다음은 한 초등학교 선생님이 작성한 프로젝트 수업 설계안입니다.\n"
                      f"GSPBL의 7가지 필수 요소(도전적인 질문, 지속적인 탐구, 진정성, 학생의 의사&선택권, 성찰, 비평과 개선, 최종 결과물 공개)와 과정중심 평가, 핵심역량, 사회정서 역량 함양 계획이 잘 반영되었는지 분석해주세요.\n"
                      f"각 요소별로 강점과 함께, 더 발전시키면 좋을 보완점을 구체적인 예시를 들어 친절하게 컨설팅해주세요.\n\n"
                      f"--- 설계안 내용 ---\n{full_plan}")
            
            st.session_state.ai_feedback = call_gemini(prompt)
        
        if st.session_state.ai_feedback:
            st.markdown(st.session_state.ai_feedback)

    image_data_list = create_lesson_plan_images()
    if image_data_list:
        st.subheader("🖼️ 수업 설계 요약표 저장")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="1페이지 JPG로 저장하기",
                data=image_data_list[0],
                file_name=f"GSPBL_설계요약표_1페이지.jpg",
                mime="image/jpeg",
                use_container_width=True,
            )
        with col2:
             st.download_button(
                label="2페이지 JPG로 저장하기",
                data=image_data_list[1],
                file_name=f"GSPBL_설계요약표_2페이지.jpg",
                mime="image/jpeg",
                use_container_width=True,
            )


# --- 6. 메인 앱 로직 ---

def main():
    initialize_session_state()

    if st.session_state.page == 0:
        render_start_page()
        st.markdown(
            """
            <style>
            .footer {
                position: fixed; left: 0; bottom: 0; width: 100%;
                background-color: transparent; color: #808080;
                text-align: center; padding: 10px; font-size: 16px;
            }
            </style>
            <div class="footer"><p>서울가동초 백인규</p></div>
            """,
            unsafe_allow_html=True
        )
    elif st.session_state.page == 1:
        render_step1()
    elif st.session_state.page == 2:
        render_step2()
    elif st.session_state.page == 3:
        render_step3()
    elif st.session_state.page == 4:
        render_step4()

    if st.session_state.page > 0:
        st.markdown("---")
        nav_cols = st.columns([1.5, 2.5, 2, 1.2, 1.2, 1.2])
        
        with nav_cols[0]:
            if st.button("🏠 처음으로", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

        with nav_cols[1]:
            st.markdown(
                """
                <div style="color: #808080; font-size: 16px; text-align: left; padding-top: 0.5rem; height: 100%; display: flex; align-items: center;">
                    서울가동초 백인규
                </div>
                """,
                unsafe_allow_html=True
            )
            
        with nav_cols[3]:
            if st.session_state.page > 1:
                if st.button("⬅️ 이전 단계", use_container_width=True):
                    st.session_state.page -= 1
                    st.rerun()
        
        with nav_cols[4]:
            if st.session_state.page < 4:
                if st.button("➡️ 다음 단계", use_container_width=True):
                    st.session_state.page += 1
                    st.rerun()
        
        with nav_cols[5]:
            if st.session_state.page == 3: # STEP 3에서만 최종 확인 버튼 표시
                if st.button("✨ 최종 확인", use_container_width=True):
                    st.session_state.page = 4
                    st.rerun()

if __name__ == "__main__":
    main()
