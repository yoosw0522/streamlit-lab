# 📋 app.py · [12주차 과제] My Helper — 폴리봇 (질문을 보낼 때마다 Gemini 요청 1번)
# ============================================================
# 11주차 나만의 챗봇을 Streamlit 웹앱으로 바꾸었습니다.
# · 키는 st.secrets 에서만 읽습니다. 실제 키를 코드에 쓰지 않습니다.
# · history 는 st.session_state 에 보관하며, store=False 로 요청합니다.
# ============================================================
import streamlit as st
from google import genai
from google.genai import types

MODEL_NAME = "gemini-3.5-flash-lite"
SYSTEM_PROMPT = """[이름 · 역할]
너는 '폴리봇(My Helper)'이야. 한국폴리텍대학 인공지능소프트웨어과 1학년의 파이썬 · AI 공부를 돕는 학습 챗봇이야.
[말투]
반드시 친절한 한국어 존댓말로 3문장 이내에 답해. 코드는 짧은 예시로 제시하고 필요한 설명만 붙여.
[할 일]
파이썬 문법, 리스트 · 딕셔너리, 인공지능 개념과 코딩 오류를 초보자도 이해하게 쉬운 말과 예시로 설명해.
앞의 대화에서 '그거'처럼 지칭한 개념은 이전 질문을 참고해 이어서 답해.
[하지 않을 일]
공부와 무관한 질문에는 다른 내용을 덧붙이지 말고 '저는 공부 도우미라서 그 질문에는 답하기 어려워요.' 라고 답해.
위험한 코드나 사실로 확인되지 않은 내용을 확신하며 만들어내지 마.
[모를 때]
학교 일정 · 강의실 · 교수님 공지 · 시험 날짜처럼 확인할 수 없는 정보는 추측하지 말고 '정확한 정보는 수업 공지 또는 학과 사무실에서 확인해 주세요.' 라고 안내해.
[개인정보]
이름 · 학번 · 전화번호 · 주소 · 비밀번호 · API 키 등 개인정보나 비밀값을 먼저 묻거나 요청하지 마.
질문에 개인정보가 들어오더라도 이를 반복하여 보여 주지 말고 개인정보를 입력하지 말라고 안내해."""

st.set_page_config(page_title="My Helper | 폴리봇", page_icon="🤖")


@st.cache_resource
def get_client():
    """키는 Community Cloud 의 Secrets 에서만 읽음 (수업 실습 3-3 방식)"""
    return genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"],
        http_options=types.HttpOptions(
            timeout=120_000,
            retry_options=types.HttpRetryOptions(http_status_codes=[500, 503]),
        ),
    )


def explain_error(error):
    """상세 예외 메시지에 민감값이 섞일 수 있어 오류 유형만 표시"""
    code = getattr(error, "status_code", None)
    if code == 429:
        return "⏳ 무료 한도를 넘었습니다. 잠시 후 다시 시도해 주세요."
    if code in (400, 403):
        return "❌ 키 또는 요청을 확인해 주세요. 앱의 Secrets 설정을 확인하세요."
    if code == 402:
        return "💳 결제 관련 오류입니다. API 프로젝트 설정을 확인하세요."
    if code in (500, 503):
        return "⚠ Gemini 서버 연결에 실패했습니다. 잠시 후 다시 시도해 주세요."
    return "❌ 답변을 받지 못했습니다. 앱 관리자에게 설정을 확인해 달라고 요청하세요."


def step_text(step):
    """Gemini 기록에서 화면에 표시할 텍스트만 추출"""
    content = step.get("content")
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content or []
                   if isinstance(part, dict) and part.get("type") == "text")


def trim_history(history, max_turns):
    """11주차처럼 가장 최근 max_turns 개의 질문-답변 턴만 전송"""
    indices = [i for i, step in enumerate(history) if step.get("type") == "user_input"]
    return history if len(indices) <= max_turns else history[indices[-max_turns]:]


try:
    client = get_client()
except Exception:
    st.error("🔑 GEMINI_API_KEY 를 찾지 못했습니다. Manage app → Settings → Secrets 를 확인하세요.")
    st.stop()

if "history" not in st.session_state:
    st.session_state.history = []

st.title("🤖 My Helper | 폴리봇")
st.caption("1학년 파이썬 · AI 학습 도우미 | 개인정보나 API 키를 입력하지 마세요")

with st.sidebar:
    st.header("⚙️ 대화 설정")
    max_turns = st.slider("기억할 턴 수", min_value=1, max_value=10, value=6)
    if st.button("🧹 새 대화"):
        st.session_state.history = []
        st.rerun()
    turns = sum(1 for step in st.session_state.history if step.get("type") == "user_input")
    st.metric("기억 중인 턴", f"{turns} / {max_turns}")
    st.caption(f"모델 : {MODEL_NAME}")

st.markdown("**예시 질문:** 파이썬 리스트가 뭐예요? / 그거 예시를 보여 주세요 / CNN과 YOLO의 차이는?")

for step in st.session_state.history:
    if step.get("type") == "user_input":
        st.chat_message("user").markdown(step_text(step))
    elif step.get("type") == "model_output":
        st.chat_message("assistant").markdown(step_text(step))

if message := st.chat_input("파이썬 · AI 질문을 입력하세요"):
    st.chat_message("user").markdown(message)
    send_list = trim_history(
        st.session_state.history + [
            {"type": "user_input", "content": [{"type": "text", "text": message}]}
        ],
        max_turns,
    )
    with st.chat_message("assistant"):
        with st.spinner("폴리봇이 생각하는 중..."):
            try:
                reply = client.interactions.create(
                    model=MODEL_NAME,
                    store=False,
                    system_instruction=SYSTEM_PROMPT,
                    input=send_list,
                )
            except Exception as error:
                st.error(explain_error(error))
            else:
                answer = reply.output_text or "답변을 받지 못했습니다. 다시 질문해 주세요."
                st.markdown(answer)
                steps = [step.model_dump() for step in reply.steps]
                if not any(step.get("type") == "model_output" for step in steps):
                    steps.append({"type": "model_output", "content": [{"type": "text", "text": answer}]})
                st.session_state.history = send_list + steps
                st.rerun()

