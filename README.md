# 코스피 대비 상대강도 대시보드

내 주식이 **코스피(또는 코스닥) 대비** 얼마나 강한지/약한지, 그리고 **추세적으로 얼마나 성장**하고 있는지를 한눈에 보는 Streamlit 웹앱.

## 무엇을 보여주나

1. **코스피 대비 상대 성과**
   - 종목과 지수를 같은 시작점(=100)으로 정규화해 겹쳐서 표시
   - "지수 대비 누적 초과수익률(%)" 영역 차트 → 0보다 위면 시장보다 강세
   - 예: 내 주식이 -10%여도 코스피도 -10%면 초과수익률은 0 → 종목 자체엔 문제 없음
2. **추세 성장률 (기간별)**
   - 어제 / 1주 / 1개월 / 3개월 / 6개월 / YTD / 1년 수익률을 가로 막대로 한눈에
   - 절대 수익률 + 지수 대비 초과수익률을 나란히, 색상으로 직관적으로

## 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 로 접속.

## 배포 (Streamlit Community Cloud — 무료)

> 이 앱은 API 키가 필요 없어 Streamlit Cloud에 바로 올릴 수 있습니다.

### 1단계: GitHub에 코드 올리기

**macOS 터미널.app**(Cursor 통합 터미널 말고)에서 실행:

```bash
cd ~/Projects/kospi-relative

# git 초기화 (이미 되어 있으면 생략)
git init
git branch -M main

git add app.py data.py metrics.py requirements.txt README.md .gitignore .streamlit/config.toml
git commit -m "Initial commit: kospi relative strength dashboard"
```

GitHub에서 **New repository** → 이름 `kospi-relative` → Public → Create (README 추가 안 함)

```bash
git remote add origin https://github.com/<YOUR_USERNAME>/kospi-relative.git
git push -u origin main
```

### 2단계: Streamlit Cloud에 배포

1. [share.streamlit.io](https://share.streamlit.io) 접속 → GitHub 계정으로 로그인
2. **Create app** 클릭
3. 설정:
   - **Repository**: `<YOUR_USERNAME>/kospi-relative`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. **Deploy!** 클릭 → 1~3분 후 URL 발급 (예: `https://kospi-relative-xxxxx.streamlit.app`)

### 배포 후 참고

- 코드를 push하면 Streamlit Cloud가 **자동으로 재배포**합니다.
- `.cache/`(순위 스냅샷)는 gitignore 처리되어 있어, 클라우드에서는 매번 새로 시작합니다.
- 데이터는 FinanceDataReader(네이버/KRX)를 사용하므로 **인터넷만 되면 별도 설정 없이 동작**합니다.

## 데이터

- 출처: [FinanceDataReader](https://github.com/FinanceData/FinanceDataReader) (무료, API 키 불필요)
- 지수: 코스피 `KS11`, 코스닥 `KQ11`
- 코스피 종목은 코스피지수, 코스닥 종목은 코스닥지수와 자동 비교 (사이드바에서 변경 가능)
