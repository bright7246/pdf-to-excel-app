import io
import pandas as pd
from pypdf import PdfReader
import streamlit as st

st.set_page_config(page_title="PDF 디버깅 테스트", page_icon="🔍", layout="centered")

st.title("🔍 PDF 텍스트 전체 추출 테스트")
st.write("PDF의 2페이지부터 들어있는 모든 텍스트를 그대로 수집합니다.")

uploaded_file = st.file_uploader("PDF 파일을 선택하세요.", type=["pdf"])

if uploaded_file is not None:
  try:
    reader = PdfReader(uploaded_file)
    total_pages = len(reader.pages)
    st.info(f"총 페이지 수: {total_pages}페이지")

    extracted_lines = []

    # 2페이지부터 끝까지 순회
    for index in range(1, total_pages):
      page = reader.pages[index]
      text = page.extract_text()

      if text:
        lines = text.split("\n")
        for line in lines:
          if line.strip():
            extracted_lines.append(
                {"페이지": index + 1, "추출된 내용": line.strip()}
            )

    if len(extracted_lines) > 0:
      df = pd.DataFrame(extracted_lines)
      st.success(
          f"총 {len(df)}줄의 텍스트를 추출했습니다! 아래 미리보기를 확인해"
          "주세요."
      )
      st.dataframe(df.head(20))  # 상위 20줄 미리보기

      # 엑셀 다운로드
      output = io.BytesIO()
      with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="전체텍스트")
      excel_data = output.getvalue()

      st.download_button(
          label="📥 전체 텍스트 엑셀 다운로드 (.xlsx)",
          data=excel_data,
          file_name="debug_extracted_text.xlsx",
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
      )
    else:
      st.error(
          "⚠️ 2페이지 이후에서 추출된 텍스트가 전혀 없습니다. 이 파일은"
          " 텍스트 레이어가 없는 '완전한 이미지(스캔본)' PDF입니다!"
      )

  except Exception as e:
    st.error(f"오류 발생: {e}")
