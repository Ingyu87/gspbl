import streamlit as st
import json
import io
import os
import re
import pandas as pd
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
def parse_5_6_standards_text(text_content):
    parsed_data = []
    subject_map = { '국': '국어', '사': '사회', '도': '도덕', '수': '수학', '과': '과학', '실': '실과', '체': '체육', '음': '음악', '미': '미술', '영': '영어' }
    pattern = re.compile(r'\[(6([가-힣]{1,2})\d{2}-\d{2})\]\s(.+)')
    lines = text_content.split('\n')
    for line in lines:
        match = pattern.match(line.strip())
        if match:
            full_code, subject_abbr, standard_text = match.groups()
            subject_full = subject_map.get(subject_abbr)
            if subject_full:
                parsed_data.append({ "학년군": "5~6", "교과": subject_full, "성취기준_코드": f"[{full_code}]", "성취기준": standard_text.strip() })
    return parsed_data

@st.cache_data
def load_json_data(filename):
    filepath = os.path.join('data', filename)
    if not os.path.exists(filepath):
        st.error(f"'{filepath}' 파일을 찾을 수 없습니다. 'data' 폴더 안에 있는지 확인해주세요."); return None
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
            if isinstance(data, dict) and 'content' in data: return parse_5_6_standards_text(data['content'])
            elif isinstance(data, list): return data
            else: st.error(f"'{filepath}' 파일의 형식이 올바르지 않습니다."); return None
    except Exception as e:
        st.error(f"'{filepath}' 파일 로딩 또는 파싱 중 오류: {e}"); return None

# --- 3. AI 및 엑셀 생성 함수 ---

def call_gemini(prompt, show_spinner=True):
    if not GEMINI_API_KEY: return "⚠️ AI 기능 비활성화: Gemini API 키가 설정되지 않았습니다."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        with st.spinner("🚀 Gemini AI가 선생님의 아이디어를 확장하고 있어요..."):
            response = model.generate_content(prompt)
            return response.text
    except Exception as e:
        return f"AI 응답 생성에 실패했습니다. API 키가 유효한지 확인해주세요. 오류: {e}"

# >>>>> 🌟 AI 요약 함수 및 관련 로직 제거 🌟 <<<<<
# summarize_text_for_image 함수는 더 이상 필요 없으므로 삭제합니다.

def create_excel_download():
    """세션 데이터 원본을 바탕으로 엑셀 파일을 생성합니다."""
    data = st.session_state

    plan_data = {
        "🎯 탐구 질문": data.get('project_title', ''),
        "📢 최종 결과물 공개": data.get('public_product', ''),
        "📚 교과 성취기준": "\n".join(f"• {s}" for s in data.get('selected_standards', [])),
        "💡 핵심역량": "\n".join(f"• {c}" for c in data.get('selected_core_competencies', [])),
        "🌱 사회정서 역량": "\n".join(f"• {c}" for c in data.get('selected_sel_competencies', [])),
        "🧭 지속적 탐구": data.get('sustained_inquiry', ''),
        "📈 과정중심 평가": data.get('process_assessment', ''),
        "🗣️ 학생의 의사 & 선택권": "\n".join(f"• {c}" for c in data.get('student_voice_choice', [])),
        "🔄 비평과 개선": data.get('critique_revision', ''),
        "🤔 성찰": data.get('reflection', '')
    }
    df = pd.DataFrame(list(plan_data.items()), columns=['항목', '내용'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='GSPBL_수업설계안')
        worksheet = writer.sheets['GSPBL_수업설계안']
        worksheet.column_dimensions['A'].width = 25
        worksheet.column_dimensions['B'].width = 80
        for row in worksheet.iter_rows(min_row=2, min_col=2, max_col=2):
            for cell in row:
                cell.alignment = cell.alignment.copy(wrap_text=True, vertical='top')
    processed_data = output.getvalue()
    return processed_data


# --- 4. 세션 상태 초기화 ---
def initialize_session_state():
    if "page" not in st.session_state: st.session_state.page = 0
    defaults = {
        "project_title": "", "public_product": "", "grade_group": "3-4학년군",
        "selected_subject": "국어", "selected_standards": [], 
        "selected_core_competencies": [], "selected_sel_competencies": [],
        "sustained_inquiry": "", "student_voice_choice": [],
        "critique_revision": "", "reflection": "", "process_assessment": "",
        "ai_feedback": "", "question_analysis": ""
    }
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value

# --- 5. 페이지 렌더링 함수 (이하 변경 없음) ---

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
                st.session_state.project_title = call_gemini(prompt)
                st.session_state.question_analysis = "" 
                st.rerun()
            else: st.warning("먼저 키워드를 입력해주세요.")
    st.session_state.project_title = st.text_area("프로젝트를 관통하는 핵심 질문을 입력하거나 AI 제안을 수정하세요.", value=st.session_state.project_title, height=150, label_visibility="collapsed")
    if st.button("현재 질문 유형 분석하기", use_container_width=True):
        if st.session_state.project_title:
            prompt = f"다음은 초등학생 대상 프로젝트 수업의 탐구 질문이야. 이 질문이 어떤 유형(예: 문제 해결형, 원인 탐구형, 창작 표현형, 찬반 논쟁형 등)에 해당하는지 분석하고, 왜 그렇게 생각하는지 간략하게 설명해줘.\n\n질문: \"{st.session_state.project_title}\""
            st.session_state.question_analysis = call_gemini(prompt)
        else: st.warning("먼저 탐구 질문을 입력해주세요.")
    if st.session_state.question_analysis: st.info(st.session_state.question_analysis)
    st.subheader("최종 결과물 공개 (Public Product)")
    st.session_state.public_product = st.text_area("학생들의 결과물을 누구에게, 어떻게 공개할지 구체적으로 작성하세요.", value=st.session_state.public_product, placeholder="예: 학부모님을 초청하여 '급식실 소음 줄이기' 캠페인 결과 발표회를 연다.", height=150, label_visibility="collapsed")
    if st.button("🤖 AI로 최종 산출물 제안받기", key="product_ai", use_container_width=True):
        if st.session_state.project_title:
            prompt = (f"'{st.session_state.grade_group}' 학생들을 위한 GSPBL 프로젝트의 '최종 결과물 공개' 아이디어를 5가지 제안해줘. 이 프로젝트의 탐구 질문은 '{st.session_state.project_title}'이야. 학생들이 프로젝트 결과를 교실 밖 실제 세상과 공유할 수 있는, **'{st.session_state.grade_group}' 수준에 맞는 창의적이고 다양한 방법**을 제안해줘. 번호 없이 한 줄씩만, 매번 다른 아이디어를 보여줘.")
            st.session_state.public_product = call_gemini(prompt)
            st.rerun()
        else: st.warning("탐구 질문을 먼저 입력해주세요.")

def render_step2():
    st.header("🧭 STEP 2. 학습 나침반 준비하기")
    st.caption("프로젝트를 통해 달성할 교과 성취기준과 핵심 역량을 명확히 설정합니다.")
    st.subheader("교과 성취기준 연결")
    VALID_SUBJECTS = {
        "1-2학년군": ["국어", "수학", "바른 생활", "슬기로운 생활", "즐거운 생활"],
        "3-4학년군": ["국어", "도덕", "사회", "수학", "과학", "체육", "음악", "미술", "영어"],
        "5-6학년군": ["국어", "사회", "도덕", "수학", "과학", "실과", "체육", "음악", "미술", "영어"]
    }
    def on_grade_change():
        st.session_state.selected_subject = VALID_SUBJECTS[st.session_state.grade_group][0] if VALID_SUBJECTS[st.session_state.grade_group] else ""
    grade_group = st.radio("학년군 선택", ["1-2학년군", "3-4학년군", "5-6학년군"], index=["1-2학년군", "3-4학년군", "5-6학년군"].index(st.session_state.grade_group), horizontal=True, key="grade_group", on_change=on_grade_change)
    standards_data = load_json_data(f"{grade_group}_성취기준.json")
    if standards_data:
        subjects = VALID_SUBJECTS[grade_group]
        selected_subject = st.selectbox("과목을 선택하세요.", subjects, key='selected_subject')
        if selected_subject:
            current_subject_standards = [f"{item['성취기준_코드']} {item['성취기준']}" for item in standards_data if item.get('교과') == selected_subject and item.get('성취기준_코드') and item.get('성취기준')]
            if current_subject_standards:
                st.write(f"**'{selected_subject}' 과목의 성취기준 목록입니다. 프로젝트에 연계할 기준을 모두 선택하세요.**")
                default_selection = [s for s in st.session_state.selected_standards if s in current_subject_standards]
                selected_in_current_subject = st.multiselect("성취기준 선택", options=current_subject_standards, default=default_selection, label_visibility="collapsed")
                standards_from_other_subjects = [s for s in st.session_state.selected_standards if s not in current_subject_standards]
                st.session_state.selected_standards = sorted(list(set(standards_from_other_subjects + selected_in_current_subject)))
            else: st.warning(f"'{selected_subject}' 과목에 대한 성취기준을 불러올 수 없습니다.")
    if st.session_state.selected_standards:
        st.markdown("---"); st.write("✅ **최종 선택된 성취기준 (모든 과목 누적)**")
        for std in st.session_state.selected_standards: st.success(f"{std}")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💡 핵심역량")
        core_competencies = ["자기관리 역량", "지식정보처리 역량", "창의적 사고 역량", "심미적 감성 역량", "협력적 소통 역량", "공동체 역량"]
        st.session_state.selected_core_competencies = [comp for comp in core_competencies if st.checkbox(comp, value=comp in st.session_state.selected_core_competencies, key=f"core_{comp}")]
    with col2:
        st.subheader("🌱 사회정서 역량")
        sel_competencies = ["자기 인식 역량", "자기 관리 역량", "사회적 인식 역량", "관계 기술 역량", "책임 있는 의사결정 역량"]
        st.session_state.selected_sel_competencies = [comp for comp in sel_competencies if st.checkbox(comp, value=comp in st.session_state.selected_sel_competencies, key=f"sel_{comp}")]

def render_step3():
    st.header("🚗 STEP 3. 탐구 여정 디자인하기")
    st.caption("학생들이 경험할 구체적인 탐구, 피드백, 성찰 활동을 계획합니다.")
    st.subheader("지속적 탐구 (Sustained Inquiry)")
    st.markdown("학생들은 어떤 과정을 통해 깊이 있는 탐구를 진행하게 될까요?")
    with st.expander("🤖 AI로 '지속적 탐구' 과정 제안받기", expanded=True):
        inquiry_tags = ["문제 발견 단계", "질문 만들기", "실태 조사 (설문, 관찰)", "전문가 인터뷰", "자료 및 문헌 조사", "해결 방안 탐색", "시제품/캠페인 기획", "산출물 제작", "수정 및 보완"]
        selected_tags = st.multiselect("주요 활동을 선택하여 탐구의 뼈대를 만들어보세요.", options=inquiry_tags)
        
        if st.button("선택한 활동으로 AI 과정 구체화하기"):
            if selected_tags and st.session_state.project_title:
                context_title = st.session_state.project_title
                context_product = st.session_state.public_product
                context_standards = "\n".join(f"- {s}" for s in st.session_state.selected_standards)
                context_core_comp = ", ".join(st.session_state.selected_core_competencies)
                context_sel_comp = ", ".join(st.session_state.selected_sel_competencies)
                context_tags = ", ".join(selected_tags)

                prompt = (
                    "당신은 초등 교육과정 설계 전문가입니다. GSPBL 모델에 기반하여 '지속적 탐구' 과정을 구체적으로 설계해주세요.\n\n"
                    "--- 프로젝트 기본 정보 ---\n"
                    f"**탐구 질문:** {context_title}\n"
                    f"**최종 결과물:** {context_product}\n"
                    f"**연계 성취기준:**\n{context_standards}\n"
                    f"**함양할 핵심역량:** {context_core_comp}\n"
                    f"**함양할 사회정서역량:** {context_sel_comp}\n"
                    f"**포함할 주요 활동:** {context_tags}\n\n"
                    "--- 요구 사항 ---\n"
                    "1. **매우 중요:** 당신이 설계하는 모든 탐구 과정은 최종적으로 위에 명시된 **'최종 결과물'을 완성하고 공개하는 방향으로 논리적으로 이어져야 합니다.**\n"
                    "2. 제시된 **성취기준과 학생 활동 목록의 복잡성**을 보고, 이 프로젝트가 초등학생 발달 단계 중 어느 수준(예: 저학년/중학년/고학년)에 적합한지 **스스로 판단**하여 그 수준에 맞는 구체적인 과정안을 작성해주세요.\n"
                    "3. **답변에 학년(예: 3-4학년)을 직접적으로 언급하지 마세요.** 대신, '학생들은 ~을 할 수 있습니다' 와 같이 활동 중심으로 서술해주세요.\n"
                    "4. 각 단계별로 예상되는 차시와 함께, 학생들이 사용할 만한 구체적인 디지털 도구를 추천해주세요.\n"
                    "5. 전체적인 흐름이 논리적으로 연결되도록 설계해주세요."
                )
                
                detailed_process = call_gemini(prompt)
                st.session_state.sustained_inquiry = detailed_process
            else:
                st.warning("STEP 1의 탐구 질문과 주요 활동을 먼저 입력/선택해주세요.")

    st.session_state.sustained_inquiry = st.text_area("탐구 과정을 구체적으로 작성하거나 AI 제안을 수정하세요.", value=st.session_state.sustained_inquiry, height=300, label_visibility="collapsed")

    st.subheader("과정중심 평가 (Process-based Assessment)")
    if st.button("🤖 AI로 평가 방법 제안받기", key="assessment_ai"):
        if st.session_state.project_title and st.session_state.sustained_inquiry:
            prompt = (f"초등학생 대상 GSPBL 프로젝트를 위한 '과정중심 평가' 방법을 5가지 제안해줘.\n"
                      f"프로젝트 주제: '{st.session_state.project_title}'\n"
                      f"주요 탐구 과정:\n{st.session_state.sustained_inquiry}\n\n"
                      f"위 내용에 가장 적합한 평가 방법을 구체적인 예시와 함께 제안해줘. 번호 없이 한 줄씩만.")
            st.session_state.process_assessment = call_gemini(prompt)
        else: st.warning("탐구 질문과 지속적 탐구 계획을 먼저 입력해주세요.")
    st.session_state.process_assessment = st.text_area("과정중심 평가 계획", value=st.session_state.process_assessment, placeholder="예: 자기평가 체크리스트 등", height=150, label_visibility="collapsed")
    st.subheader("학생의 의사 & 선택권 (Student Voice and Choice)")
    voice_options = {"모둠 구성 방식": False, "자료 수집 방법": False, "산출물 형태 (영상, 포스터 등)": False, "역할 분담": False, "발표 방식": False}
    st.session_state.student_voice_choice = [option for option, _ in voice_options.items() if st.checkbox(option, value=option in st.session_state.student_voice_choice)]
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("비평과 개선 (Critique & Revision)")
        if st.button("🤖 AI로 비평/개선 방법 제안받기", key="critique_ai"):
             if st.session_state.project_title:
                prompt = f"초등학생 대상 GSPBL 프로젝트를 위한 '비평과 개선(Critique & Revision)' 활동 아이디어를 5가지 제안해줘. 이 프로젝트의 주제는 '{st.session_state.project_title}'이고, 최종 결과물은 '{st.session_state.public_product}'이야. 학생들이 서로 의미 있는 피드백을 주고받고, 자신의 결과물을 발전시킬 수 있는 구체적이고 창의적인 방법을 제안해줘. 번호 없이 한 줄씩만."
                st.session_state.critique_revision = call_gemini(prompt)
             else: st.warning("STEP 1의 탐구 질문을 먼저 입력해주세요.")
        st.session_state.critique_revision = st.text_area("피드백 계획", value=st.session_state.critique_revision, placeholder="AI 제안을 받거나 직접 입력하세요.", height=200, label_visibility="collapsed")
    with col2:
        st.subheader("성찰 (Reflection)")
        if st.button("🤖 AI로 성찰 방법 제안받기", key="reflection_ai"):
            if st.session_state.project_title:
                prompt = f"초등학생 대상 GSPBL 프로젝트를 위한 '성찰(Reflection)' 활동 아이디어를 5가지 제안해줘. 이 프로젝트의 주제는 '{st.session_state.project_title}'이야. 학생들이 프로젝트 과정 전반에 걸쳐 자신의 학습, 성장, 느낀 점을 의미 있게 돌아볼 수 있는 구체적이고 창의적인 방법을 제안해줘. 번호 없이 한 줄씩만."
                st.session_state.reflection = call_gemini(prompt)
            else: st.warning("STEP 1의 탐구 질문을 먼저 입력해주세요.")
        st.session_state.reflection = st.text_area("성찰 계획", value=st.session_state.reflection, placeholder="AI 제안을 받거나 직접 입력하세요.", height=200, label_visibility="collapsed")

def render_step4():
    st.header("✨ STEP 4. 최종 설계도 확인 및 내보내기")
    st.caption("입력된 모든 내용을 하나의 문서로 통합하여 확인하고, 저장 및 공유할 수 있습니다.")
    st.markdown("---")
    final_data = {
        "🎯 탐구 질문": "project_title", "📢 최종 결과물 공개": "public_product",
        "📚 교과 성취기준": "selected_standards", "💡 핵심역량": "selected_core_competencies",
        "🌱 사회정서 역량": "selected_sel_competencies", "🧭 지속적 탐구": "sustained_inquiry",
        "📈 과정중심 평가": "process_assessment", "🗣️ 학생의 의사 & 선택권": "student_voice_choice",
        "🔄 비평과 개선": "critique_revision", "🤔 성찰": "reflection"
    }
    for title, key in final_data.items():
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.subheader(title)
                content = st.session_state.get(key, "")
                if isinstance(content, list): st.write("\n".join(f"- {item}" for item in content) if content else "입력된 내용이 없습니다.")
                else: st.write(content if content else "입력된 내용이 없습니다.")
            with col2:
                if st.button(f"✏️ 수정", key=f"edit_{key}", use_container_width=True):
                    if key in ["project_title", "public_product"]: st.session_state.page = 1
                    elif key in ["selected_standards", "selected_core_competencies", "selected_sel_competencies"]: st.session_state.page = 2
                    else: st.session_state.page = 3
                    st.rerun()
    st.markdown("---")
    with st.expander("🤖 AI에게 수업 설계안 종합 피드백 받기"):
        if st.button("피드백 요청하기", use_container_width=True):
            full_plan = ""
            for title, key in final_data.items():
                content = st.session_state.get(key, "")
                content_str = "\n".join(content) if isinstance(content, list) else content
                full_plan += f"### {title}\n{content_str}\n\n"
            prompt = (f"당신은 GSPBL(Gold Standard Project Based Learning) 전문가입니다.\n다음은 한 초등학교 선생님이 작성한 프로젝트 수업 설계안입니다.\nGSPBL의 7가지 필수 요소와 과정중심 평가, 핵심역량, 사회정서 역량 함양 계획이 잘 반영되었는지 분석해주세요.\n각 요소별로 강점과 함께, 더 발전시키면 좋을 보완점을 구체적인 예시를 들어 친절하게 컨설팅해주세요.\n\n--- 설계안 내용 ---\n{full_plan}")
            st.session_state.ai_feedback = call_gemini(prompt)
        if st.session_state.ai_feedback: st.markdown(st.session_state.ai_feedback)
    
    st.subheader("📋 수업 설계안 저장")
    st.markdown("---")
    
    excel_data = create_excel_download()
    
    st.download_button(
        label="📥 수업 설계안 엑셀(Excel) 파일로 저장하기",
        data=excel_data,
        file_name=f"GSPBL_수업설계안.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary"
    )

# --- 6. 메인 앱 로직 ---
def main():
    initialize_session_state()
    page_functions = {0: render_start_page, 1: render_step1, 2: render_step2, 3: render_step3, 4: render_step4}
    page_functions[st.session_state.page]()
    if st.session_state.page > 0:
        st.markdown("---")
        nav_cols = st.columns([1.5, 2.5, 2, 1.2, 1.2, 1.2])
        with nav_cols[0]:
            if st.button("🏠 처음으로", use_container_width=True):
                for key in list(st.session_state.keys()): del st.session_state[key]
                st.rerun()
        with nav_cols[1]:
            st.markdown("""<div style="color: #808080; font-size: 16px; text-align: left; padding-top: 0.5rem; height: 100%; display: flex; align-items: center;">서울가동초 백인규</div>""", unsafe_allow_html=True)
        with nav_cols[3]:
            if st.session_state.page > 1:
                if st.button("⬅️ 이전 단계", use_container_width=True): st.session_state.page -= 1; st.rerun()
        with nav_cols[4]:
            if st.session_state.page < 4:
                if st.button("➡️ 다음 단계", use_container_width=True): st.session_state.page += 1; st.rerun()
        with nav_cols[5]:
            if st.session_state.page == 4:
                if st.button("🎉 새 설계", use_container_width=True, type="primary"):
                    for key in list(st.session_state.keys()): del st.session_state[key]
                    st.rerun()
    else:
        st.markdown("""<style>.footer {position: fixed; left: 0; bottom: 0; width: 100%; background-color: transparent; color: #808080; text-align: center; padding: 10px; font-size: 16px;}</style><div class="footer"><p>서울가동초 백인규</p></div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()