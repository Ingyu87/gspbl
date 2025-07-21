GSPBL 수업 설계 내비게이터: GitHub & Streamlit 배포 안내서
이 문서는 'GSPBL 수업 설계 내비게이터' Streamlit 웹앱을 GitHub에 올리고, Streamlit Community Cloud를 통해 웹에 무료로 배포하는 전체 과정을 안내합니다.

✅ 0단계: 준비물 확인
배포를 시작하기 전에 아래 항목들이 준비되었는지 확인해주세요.

GitHub 계정: 코드를 올릴 저장 공간입니다.

Streamlit Community Cloud 계정: 앱을 배포하고 실행할 플랫폼입니다. (GitHub 계정으로 가입 가능)

Gemini API 키: 앱의 AI 기능을 사용하기 위한 필수 키입니다. Google AI Studio에서 발급받을 수 있습니다.

📂 1단계: 프로젝트 폴더 구성하기
배포할 프로젝트 폴더가 아래와 같은 구조로 되어 있는지 다시 한번 확인하고, 필요한 파일을 정확한 위치에 준비하세요.

GSPBL-Navigator/
│
├── 📁 data/
│   ├── 📄 1-2학년군_성취수준.json
│   ├── 📄 3-4학년군_성취수준.json
│   ├── 📄 5-6학년군_성취수준.json
│   └── 📄 Pretendard-Regular.ttf
│
├── 📄 app.py
└── 📄 requirements.txt

1. requirements.txt 파일 생성 및 내용 확인:

app.py와 같은 위치에 requirements.txt 파일이 있는지 확인하세요.

파일 안에 아래 내용이 정확하게 들어있는지 확인하고, 없다면 복사하여 붙여넣고 저장하세요.

streamlit
Pillow
google-generativeai

2. data 폴더 확인:

app.py와 같은 위치에 data 폴더가 있는지 확인하세요.

data 폴더 안에 3개의 .json 파일과 Pretendard-Regular.ttf 폰트 파일이 모두 들어있는지 확인하세요.

☁️ 2단계: GitHub에 프로젝트 올리기
새 저장소(Repository) 만들기:

GitHub에 로그인 후 New repository를 클릭합니다.

Repository name: gspbl-navigator (또는 원하는 다른 이름)

Public (공개)으로 설정합니다.

Create repository 버튼을 클릭하여 새 저장소를 만듭니다.

파일 및 폴더 업로드 (가장 쉬운 방법):

방금 만든 저장소 페이지에서 Add file > Upload files를 클릭합니다.

컴퓨터에 있는 app.py 파일, requirements.txt 파일, 그리고 data 폴더 자체를 모두 선택하여 웹 브라우저의 업로드 영역으로 끌어다 놓습니다.

업로드가 완료되면 페이지 하단의 Commit changes 버튼을 클릭하여 저장합니다.

🚀 3단계: Streamlit Community Cloud로 앱 배포하기
Streamlit Community Cloud 사이트에 GitHub 계정으로 로그인합니다.

새 앱 배포 (New app):

화면 우측 상단의 New app 버튼을 클릭합니다.

Repository: 방금 생성한 gspbl-navigator 저장소를 선택합니다.

Branch: main

Main file path: app.py (자동으로 설정됩니다.)

Advanced settings...를 클릭하여 추가 설정을 엽니다.

Secrets: 이 칸에 아래 내용을 그대로 복사하여 붙여넣습니다. "YOUR_API_KEY_HERE" 부분은 반드시 본인의 실제 Gemini API 키로 교체해야 합니다.

GEMINI_API_KEY = "YOUR_API_KEY_HERE"

배포 시작:

Save 버튼을 눌러 Secrets를 저장한 후, Deploy! 버튼을 클릭합니다.

배포가 시작되며, 잠시 후 나만의 GSPBL 내비게이터 웹앱이 완성됩니다!