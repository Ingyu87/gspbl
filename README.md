# GSPBL 수업 설계 내비게이터: GitHub & Streamlit 배포 안내서

이 문서는 'GSPBL 수업 설계 내비게이터' Streamlit 웹앱을 GitHub에 올리고, Streamlit Community Cloud를 통해 웹에 무료로 배포하는 과정을 안내합니다. (data 폴더 구조 적용 버전)

---

### 📂 1단계: 프로젝트 폴더 구성하기

배포를 시작하기 전에, 컴퓨터에 있는 프로젝트 폴더가 **아래와 같은 구조**로 되어 있는지 확인하고 필요한 파일을 생성 및 이동하세요.


GSPBL-APP/
│
├── 📁 data/                    # 데이터 및 폰트 보관용 폴더
│   ├── 📄 1-2학년군_성취수준.json
│   ├── 📄 3-4학년군_성취수준.json
│   ├── 📄 5-6학년군_성취수준.json
│   └── 📄 Pretendard-Regular.ttf  # 사용할 폰트 파일
│
├── 📄 app.py                   # 스트림릿 앱 메인 코드
└── 📄 requirements.txt         # 필요한 파이썬 라이브러리 목록


**1. `data` 폴더 생성:**
   - 프로젝트 폴더(`GSPBL-APP`) 안에 `data` 라는 이름의 새 폴더를 만듭니다.

**2. 파일 이동 및 준비:**
   - **3개의 `.json` 파일**을 모두 `data` 폴더 안으로 이동시킵니다.
   - 방금 올려주신 **`Pretendard-Regular.ttf`** 폰트 파일을 `data` 폴더 안에 넣습니다.

**3. `requirements.txt` 파일 생성:**
   - **`app.py`와 같은 위치**에 `requirements.txt` 라는 이름의 새 텍스트 파일을 만드세요.
   - 파일 안에 다음 세 줄을 복사하여 붙여넣고 저장하세요.
     ```
     streamlit
     Pillow
     google-generativeai
     ```

---

### ☁️ 2단계: GitHub에 프로젝트 올리기

1.  **새 저장소(Repository) 만들기:**
    * [GitHub](https://github.com/)에 로그인 후 `New repository`를 클릭합니다.
    * Repository name: `gspbl-app`
    * `Public` (공개)으로 설정합니다.
    * `Create repository` 버튼을 클릭합니다.

2.  **파일 및 폴더 업로드:**
    * 만든 저장소 페이지에서 `Add file` > `Upload files`를 클릭합니다.
    * `app.py`와 `requirements.txt` 파일을 끌어다 놓아 업로드합니다.
    * 업로드가 완료되면 `Commit changes`를 클릭합니다.
    * 다시 저장소 첫 화면으로 돌아와, `Add file` > `Create new file`을 클릭합니다.
    * 파일 이름 입력 칸에 **`data/`** 라고 입력하면 폴더가 생성됩니다.
    * 이제 생성된 `data` 폴더로 이동하여, 위와 같은 방법으로 `Upload files`를 통해 **3개의 JSON 파일과 `Pretendard-Regular.ttf` 폰트 파일**을 업로드합니다.

---

### 🚀 3단계: Streamlit Community Cloud로 앱 배포하기

1.  **[Streamlit Community Cloud](https://share.streamlit.io/)** 사이트에 GitHub 계정으로 로그인합니다.

2.  **새 앱 배포 (`New app`):**
    * **Repository:** 방금 생성한 `gspbl-app` 저장소를 선택합니다.
    * **Branch:** `main`
    * **Main file path:** `app.py`
    * `Deploy!` 버튼을 클릭합니다.

3.  **(최초 배포 시) Gemini API 키 설정:**
    * 앱이 배포된 후, 오른쪽 상단의 `Manage app` > `Settings` > `Secrets` 메뉴로 이동합니다.
    * `Secrets` 텍스트 박스에 아래 내용을 붙여넣고 `Save`를 클릭합니다. **(YOUR_API_KEY 부분은 실제 Gemini API 키로 교체해야 합니다.)**
      ```
      GEMINI_API_KEY = "YOUR_API_KEY_HERE"
      ```
    * API 키를 저장한 후, `Reboot app`을 눌러 앱을 재시작하면 AI 기능이 활성화됩니다.

이제 모든 설정이 완료되었습니다!
