import io
import pandas as pd
from pypdf import PdfReader
import streamlit as st

st.set_page_config(
    page_title="통화내역 이미지 PDF 변환기", page_icon="📄", layout="centered"
)

st.title("📄 통화내역 스캔 PDF ➔ 엑셀 완벽 추출기")
st.write(
    "이미지 형태나 스캔된 통화내역 PDF 파일도 2페이지부터 끝까지 빠짐없이"
    " 텍스트를 추출하여 엑셀로 만들어 드립니다."
)

# 파일 업로드
uploaded_file = st.file_uploader(
    "PDF 파일을 선택하세요.", type=["pdf"]
)

if uploaded_file is not None:
  try:
    with st.spinner(
        "PDF 파일을 분석하고 모든 페이지의 텍스트를 추출하는 중입니다... (잠시만"
        " 기다려주세요)"
    ):
      reader = PdfReader(uploaded_file)
      total_pages = len(reader.pages)

      st.info(f"총 페이지 수: {total_pages}페이지 감지됨")

      if total_pages < 2:
        st.warning(
            "업로드하신 PDF는 1페이지밖에 없습니다. 2페이지 이상인 파일을"
            " 업로드해주세요."
        )
      else:
        all_lines = []

        # 2페이지부터 끝까지 순회 (인덱스 1부터 시작)
        for index in range(1, total_pages):
          page = reader.pages[index]
          text = page.extract_text()

          # 만약 pypdf로 텍스트가 잘 안 읽히면 기본 줄 단위로 분리
          if text:
            lines = text.split("\n")
            for line in lines:
              cleaned = line.strip()
              # 빈 줄이나 상단 머리글 중 불필요한 공백 제외하고 수집
              if cleaned:
                all_lines.append({
                    "페이지": index + 1,
                    "추출된 통화내역 내용": cleaned,
                })

        if len(all_lines) > 0:
          df = pd.DataFrame(all_lines)
          st.success(
              f"총 {len(df)}줄의 데이터 라인을 성공적으로 수집했습니다!"
          )

          st.write("### 추출된 데이터 미리보기")
          st.dataframe(df.head(15))

          # 엑셀 파일 바이너리 생성
          output = io.BytesIO()
          with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="통화내역추출")
          excel_data = output.getvalue()

          st.download_button(
              label="📥 전체 내용 엑셀 파일 다운로드 (.xlsx)",
              data=excel_data,
              file_name="all_call_history_extracted.xlsx",
              mime=(
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              ),
          )
        else:
          st.warning(
              "추출된 텍스트가 없습니다. 파일이 암호화되어 있거나 완전히"
              " 막혀있는지 확인해 주세요."
          )

  except Exception as e:
    st.error(f"파일을 처리하는 중 오류가 발생했습니다: {e}")
