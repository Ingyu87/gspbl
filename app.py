import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
import os
import google.generativeai as genai

# --- 1. 초기 설정 및 API 키 구성 ---
st.set_page_config(
    page_title="GSPBL 수업 설계 내비게이터",
    page_icon="🚀",
    layout="centered",
    initial_sidebar_state="auto",
)

# Gemini API 키 설정
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except (FileNotFoundError, KeyError):
    GEMINI_API_KEY = "" # 로컬 테스트 시 여기에 키 입력

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"API 키 설정 중 오류가 발생했습니다: {e}")
else:
    st.warning("Gemini API 키가 설정되지 않았습니다. AI 기능을 사용하려면 앱 설정(Secrets)에 키를 추가하거나 코드에 직접 입력해주세요.")


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

# 🌟🌟🌟 AI 요약 함수 추가 🌟🌟🌟
def summarize_text_for_image(text, max_chars=400):
    """이미지 생성을 위해 긴 텍스트를 AI로 요약하거나 단순 축약합니다."""
    if not isinstance(text, str) or len(text) <= max_chars:
        return text

    # API 키가 없으면 단순 축약
    if not GEMINI_API_KEY:
        return text[:max_chars] + "..."

    try:
        # 이미지 생성 중에는 별도의 스피너 없이 내부적으로 호출
        prompt = f"다음 텍스트를 최종 보고서의 요약표에 넣을 수 있도록 200자 내외의 핵심 내용으로 매우 간결하게 요약해줘:\n\n---\n{text}\n---"
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        # API 실패 시 안전하게 단순 축약으로 대체
        return text[:max_chars] + "..."

# 🌟🌟🌟 이미지 생성 함수 수정 🌟🌟🌟
def create_lesson_plan_images():
    """세션 데이터를 '요약'하여 2페이지 분량의 이미지를 생성합니다."""
    original_data = st.session_state
    
    # 1. 이미지에 표시할 데이터만 따로 요약/가공
    display_data = {}
    fields_to_summarize = [
        'sustained_inquiry', 'process_assessment', 
        'critique_revision', 'reflection', 'public_product'
    ]
    for key, value in original_data.items():
        if key in fields_to_summarize:
            display_data[key] = summarize_text_for_image(value)
        elif key == 'selected_standards' and isinstance(value, list):
            # 성취기준은 4개까지만 보여주고 나머지는 개수로 표시
            if len(value) > 4:
                display_data[key] = value[:4] + [f"...외 {len(value) - 4}개 항목"]
            else:
                display_data[key] = value
        else:
            # 그 외의 데이터는 그대로 복사
            display_data[key] = value

    # 2. 요약된 데이터를 기반으로 페이지별 내용 구성
    rows_page1 = {
        "🎯 탐구 질문": display_data.get('project_title', ''),
        "📢 최종 결과물 공개": display_data.get('public_product', ''),
        "📚 교과 성취기준": "\n".join(display_data.get('selected_standards', [])),
        "💡 핵심역량": "\n".join(f"• {c}" for c in display_data.get('selected_core_competencies', [])),
        "🌱 사회정서 역량": "\n".join(f"• {c}" for c in display_data.get('selected_sel_competencies', [])),
    }
    
    rows_page2 = {
        "🧭 지속적 탐구": display_data.get('sustained_inquiry', ''),
        "📈 과정중심 평가": display_data.get('process_assessment', ''),
        "🗣️ 학생의 의사 & 선택권": "\n".join(f"• {c}" for c in display_data.get('student_voice_choice', [])),
        "🔄 비평과 개선": display_data.get('critique_revision', ''),
        "🤔 성찰": display_data.get('reflection', '')
    }

    # 3. 이미지 생성 (기존 로직과 거의 동일)
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
                wrapped_lines = textwrap.wrap(line, width=int(w / (font.size * 0.55)), break_long_words=True, replace_whitespace=False)
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
                
                if y_text + line_height < y + h:
                    draw.text((x_text, y_text), line, font=font, fill=text_color)
                    y_text += line_height
        
        y_pos = margin
        draw.rectangle([(margin, y_pos), (width - margin, y_pos + 80)], fill=header_bg_color, outline=line_color)
        draw_multiline_text_in_box(f"GSPBL 수업 설계도 ({page_num}/2)", title_font, (margin, y_pos, width - margin*2, 80), h_align='center', v_align='center')
        y_pos += 80 + 10

        for header, content in rows.items():
            lines = []
            for line in str(content).split('\n'):
                wrapped_lines = textwrap.wrap(line, width=65)
                lines.extend(wrapped_lines if wrapped_lines else [''])
            row_height = max(100, len(lines) * 30 + 40)
            
            if y_pos + row_height > height - margin:
                row_height = height - margin - y_pos

            draw.rectangle([(margin, y_pos), (margin + 300, y_pos + row_height)], fill=(245, 245, 245), outline=line_color)
            draw_multiline_text_in_box(header, header_font, (margin, y_pos, 300, row_height), v_align='center', h_align='center')
            draw.rectangle([(margin + 300, y_pos), (width - margin, y_pos + row_height)], fill='white', outline=line_color)
            draw_multiline_text_in_box(str(content), body_font, (margin + 300, y_pos, width - margin*2 - 300, row_height))
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
        "grade_group": "3-4학년군",
        "selected_subject": "국어",
        "selected_standards": [], 
        "selected_core_competencies": [], "selected_sel_competencies": [],
        "sustained_inquiry": "", "student_voice_choice": [],
        "critique_revision": "", "reflection": "", "process_assessment": "",
        "ai_feedback": "",
        "question_analysis": ""
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- 5. 페이지 렌더링 함수 ---

def render_start_page():
    st.title("GSPBL 수업 설계 내비게이터 🚀")
    st.markdown("---")
    st.subheader("선생님의 아이디어가 학생들의 삶을 바꾸는 진짜 배움으로 연결되도록,")
    st.subheader("GSPBL 내비게이터가 단계별 설계를 안내합니다.")
    st.write("")
    if st.button("➕ 새 프로젝트 설계 시작하기", type="primary", use_container_width=True):
        st.session_state.page = 1
        st.rerun()

def render_step1():
    st.header("🗺️ STEP 1. 최종 목적지 설정하기")
    st.caption("프로젝트의 핵심이 되는 탐구 질문과 최종 결과물을 설정합니다.")
    
    st.subheader("탐구 질문 (Challenging Problem or Question)")
    
    with st.expander("🤖 AI 도우미: 탐구 질문 만들기", expanded=True):
        ai_keyword = st.text_input("질문 아이디어를 얻고 싶은 분야(키워드)를 입력하세요.", placeholder="예: 기후 위기, 우리 동네 문제, 재활용")
        
        if st.button("입력한 분야로 질문 제안받기", use_container_width=True):
            if ai_keyword:
                prompt = f"초등학생 대상 GSPBL 프로젝트를 위한 '탐구 질문'을 생성해줘. 핵심 키워드는 '{ai_keyword}'야. 학생들이 흥미를 느끼고 깊이 탐구하고 싶게 만드는, 정답이 없는 질문 5개를 제안해줘. 번호 없이 한 줄씩만."
                suggestions = call_gemini(prompt)
                st.session_state.project_title = suggestions
                st.session_state.question_analysis = "" 
                st.rerun()
            else:
                st.warning("먼저 키워드를 입력해주세요.")
    
    st.session_state.project_title = st.text_area(
        "프로젝트를 관통하는 핵심 질문을 입력하거나 AI 제안을 수정하세요.",
        value=st.session_state.project_title,
        height=150,
        label_visibility="collapsed"
    )

    if st.button("현재 질문 유형 분석하기", use_container_width=True):
        if st.session_state.project_title:
            prompt = f"다음은 초등학생 대상 프로젝트 수업의 탐구 질문이야. 이 질문이 어떤 유형(예: 문제 해결형, 원인 탐구형, 창작 표현형, 찬반 논쟁형 등)에 해당하는지 분석하고, 왜 그렇게 생각하는지 간략하게 설명해줘.\n\n질문: \"{st.session_state.project_title}\""
            analysis = call_gemini(prompt)
            st.session_state.question_analysis = analysis
        else:
            st.warning("먼저 탐구 질문을 입력해주세요.")
    
    if st.session_state.question_analysis:
        st.info(st.session_state.question_analysis)


    st.subheader("최종 결과물 공개 (Public Product)")
    st.session_state.public_product = st.text_area(
        "학생들의 결과물을 누구에게, 어떻게 공개할지 구체적으로 작성하세요.",
        value=st.session_state.public_product,
        placeholder="예: 학부모님을 초청하여 '급식실 소음 줄이기' 캠페인 결과 발표회를 연다.",
        height=150,
        label_visibility="collapsed"
    )
    if st.button("🤖 AI로 최종 산출물 제안받기", key="product_ai", use_container_width=True):
        if st.session_state.project_title:
            prompt = f"초등학생 대상 GSPBL 프로젝트를 위한 '최종 결과물 공개(Public Product)' 아이디어를 5가지 제안해줘. 이 프로젝트의 탐구 질문은 '{st.session_state.project_title}'이야. 학생들이 프로젝트 결과를 교실 밖 실제 세상과 공유할 수 있는 구체적이고 의미 있는 방법을 제안해줘. 번호 없이 한 줄씩만."
            suggestions = call_gemini(prompt)
            st.session_state.public_product = suggestions
            st.rerun()
        else:
            st.warning("탐구 질문을 먼저 입력해주세요.")

def render_step2():
    st.header("🧭 STEP 2. 학습 나침반 준비하기")
    st.caption("프로젝트를 통해 달성할 교과 성취기준과 핵심 역량을 명확히 설정합니다.")

    st.subheader("교과 성취기준 연결")

    VALID_SUBJECTS = {
        "1-2학년군": ["국어", "수학", "바른 생활", "슬기로운 생활", "즐거운 생활"],
        "3-4학년군": ["국어", "도덕", "사회", "수학", "과학", "체육", "음악", "미술", "영어"],
        "5-6학년군": []
    }

    def on_grade_change():
        st.session_state.selected_subject = VALID_SUBJECTS[st.session_state.grade_group][0] if VALID_SUBJECTS[st.session_state.grade_group] else ""

    grade_group = st.radio(
        "학년군 선택",
        ["1-2학년군", "3-4학년군", "5-6학년군"],
        index=["1-2학년군", "3-4학년군", "5-6학년군"].index(st.session_state.grade_group),
        horizontal=True,
        key="grade_group",
        on_change=on_grade_change
    )

    if grade_group == "5-6학년군":
        st.info("🚧 5-6학년군 성취기준 데이터는 현재 준비 중입니다. 추후 업데이트될 예정입니다.")
    else:
        filename = f"{grade_group}_성취기준.json"
        standards_data = load_json_data(filename)

        if standards_data:
            subjects = VALID_SUBJECTS[grade_group]
            
            selected_subject = st.selectbox(
                "과목을 선택하세요.",
                subjects,
                key='selected_subject'
            )

            if selected_subject:
                current_subject_standards = [
                    f"{item['성취기준_코드']} {item['성취기준']}"
                    for item in standards_data
                    if item.get('교과') == selected_subject and item.get('성취기준_코드') and item.get('성취기준')
                ]
                
                if current_subject_standards:
                    st.write(f"**'{selected_subject}' 과목의 성취기준 목록입니다. 프로젝트에 연계할 기준을 모두 선택하세요.**")
                    
                    default_selection = [
                        s for s in st.session_state.selected_standards 
                        if s in current_subject_standards
                    ]

                    selected_in_current_subject = st.multiselect(
                        "성취기준 선택",
                        options=current_subject_standards,
                        default=default_selection,
                        label_visibility="collapsed"
                    )

                    standards_from_other_subjects = [
                        s for s in st.session_state.selected_standards 
                        if s not in current_subject_standards
                    ]
                    
                    st.session_state.selected_standards = sorted(list(set(standards_from_other_subjects + selected_in_current_subject)))

                else:
                    st.warning(f"'{selected_subject}' 과목에 대한 성취기준을 불러올 수 없습니다.")
        else:
            st.error(f"'{filename}' 파일을 불러오는 데 실패했습니다. 파일이 'data' 폴더에 있는지 확인해주세요.")

    if st.session_state.selected_standards:
        st.markdown("---")
        st.write("✅ **최종 선택된 성취기준 (모든 과목 누적)**")
        for std in st.session_state.selected_standards:
            st.success(f"{std}")

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
                          f"프로젝트의 탐구 질문은 '{st.session_state.project_title}'이야.\n"
                          f"다음과 같은 활동들을 포함해서, 각 단계별로 학생들이 무엇을 할지, 어떤 디지털 도구를 사용하면 좋을지 예시를 들어 간단한 과정안(1차시 : 40분)을 작성해줘.\n\n"
                          f"포함할 활동: {', '.join(selected_tags)}")
                detailed_process = call_gemini(prompt)
                st.session_state.sustained_inquiry = detailed_process
            else:
                st.warning("탐구 질문과 주요 활동을 먼저 입력/선택해주세요.")

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
            st.warning("탐구 질문과 지속적 탐구 계획을 먼저 입력해주세요.")

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
                st.warning("STEP 1의 탐구 질문을 먼저 입력해주세요.")
        
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
                st.warning("STEP 1의 탐구 질문을 먼저 입력해주세요.")

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
        "🎯 탐구 질문": "project_title",
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

    # 🌟🌟🌟 이미지 생성 시 스피너 및 안내 문구 추가 🌟🌟🌟
    with st.spinner("요약 이미지를 생성하고 있습니다... (내용이 길 경우 AI 요약이 포함됩니다)"):
        image_data_list = create_lesson_plan_images()

    if image_data_list:
        st.subheader("🖼️ 수업 설계 요약표 저장")
        st.caption("ℹ️ 내용이 긴 항목(지속적 탐구 등)과 성취기준 개수가 많은 경우, 이미지에 맞게 요약/축약되어 표시됩니다.")
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

    page_functions = {
        0: render_start_page,
        1: render_step1,
        2: render_step2,
        3: render_step3,
        4: render_step4,
    }
    page_functions[st.session_state.page]()

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
            if st.session_state.page == 4:
                if st.button("🎉 새 설계", use_container_width=True, type="primary"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
    else:
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

if __name__ == "__main__":
    main()