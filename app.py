import io
import pandas as pd
from pypdf import PdfReader
import streamlit as st

st.set_page_config(
    page_title="통화내역 PDF 변환기", page_icon="📄", layout="centered"
)

st.title("📄 통화내역 PDF ➔ 엑셀 변환기")
st.write(
    "업로드하신 PDF 파일의 2페이지부터 끝까지의 텍스트를 추출하여 엑셀로"
    " 변환해 드립니다."
)

# 파일 업로드
uploaded_file = st.file_uploader(
    "PDF 파일을 선택하세요.", type=["pdf"]
)

if uploaded_file is not None:
  try:
    with st.spinner("PDF 파일을 분석하고 데이터를 추출하는 중입니다..."):
      reader = PdfReader(uploaded_file)
      total_pages = len(reader.pages)

      st.info(f"총 {total_pages}페이지가 감지되었습니다.")

      if total_pages < 2:
        st.warning(
            "업로드하신 PDF는 1페이지밖에 없습니다. 2페이지 이상인 파일을"
            " 업로드해주세요."
        )
      else:
        extracted_data = []

        # 2페이지부터 끝까지 순회 (인덱스 1부터 시작)
        for index in range(1, total_pages):
          page = reader.pages[index]
          text = page.extract_text()

          if text:
            lines = text.split("\n")
            for line_idx, line in enumerate(lines):
              cleaned_line = line.strip()
              if cleaned_line:
                # 상단 머리글 등은 제외하고 의미 있는 내용만 담기
                if not any(
                    kw in cleaned_line
                    for kw in ["개인정보유출주의", "다운로드일시"]
                ):
                  extracted_data.append({
                      "페이지": index + 1,
                      "라인번호": line_idx + 1,
                      "추출내용": cleaned_line,
                  })

        if len(extracted_data) > 0:
          df = pd.DataFrame(extracted_data)
          st.success(
              f"총 {len(df)}건의 텍스트 데이터를 성공적으로 추출했습니다!"
          )

          st.write("### 추출된 데이터 미리보기 (상위 15행)")
          st.dataframe(df.head(15))

          # 엑셀 파일 바이너리 생성
          output = io.BytesIO()
          with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="통화내역추출")
          excel_data = output.getvalue()

          st.download_button(
              label="📥 변환된 엑셀 파일 다운로드 (.xlsx)",
              data=excel_data,
              file_name="call_history_extracted.xlsx",
              mime=(
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              ),
          )
        else:
          st.warning(
              "2페이지 이후에서 추출된 텍스트가 없습니다. 법원/통신사에서"
              " 발급받은 PDF가 완전히 이미지로만 구성된 파일인지 확인해"
              " 주세요."
          )

  except Exception as e:
    st.error(f"파일을 처리하는 중 오류가 발생했습니다: {e}")
