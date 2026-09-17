import io
import re
import pandas as pd
from pypdf import PdfReader
import streamlit as st

st.set_page_config(
    page_title="통화내역 표 추출기", page_icon="📊", layout="centered"
)

st.title("📊 통화내역 표 구조 엑셀 변환기")
st.write(
    "스캔본 PDF의 2페이지 표 구조(사업자, 순번, 사용유형, 착신번호,"
    " 통화시작시간 등)를 분석하여 엑셀 파일로 변환합니다."
)

uploaded_file = st.file_uploader(
    "PDF 파일을 선택하세요.", type=["pdf"]
)

if uploaded_file is not None:
  try:
    with st.spinner("PDF 파일 분석 및 표 데이터 추출 중..."):
      reader = PdfReader(uploaded_file)
      total_pages = len(reader.pages)

      st.info(f"총 {total_pages}페이지가 감지되었습니다.")

      if total_pages < 2:
        st.warning("2페이지 이상인 파일을 업로드해주세요.")
      else:
        extracted_rows = []

        # 2페이지(인덱스 1) 집중 분석
        page = reader.pages[1]
        text = page.extract_text()

        if text:
          lines = text.split("\n")
          for line in lines:
            line_str = line.strip()

            # 통신사명(LGU+, SKT, KT 등)으로 시작하고 번호/시간 패턴이 포함된 행 탐지
            if any(
                line_str.startswith(tel)
                for tel in ["LGU+", "SKT", "KT", "LG", "SK"]
            ):
              # 공백 기준으로 데이터 분리
              parts = re.split(r"\s{2,}", line_str)

              if len(parts) >= 6:
                extracted_rows.append({
                    "사업자": parts[0],
                    "순번": parts[1],
                    "사용유형": parts[2],
                    "착신번호": parts[3],
                    "통화시작시간": parts[4],
                    "사용시간(초)": parts[5],
                    "발신기지국주소": parts[6] if len(parts) > 6 else "",
                })
              else:
                # 단일 공백 기준으로 유연하게 파싱
                tokens = line_str.split()
                if len(tokens) >= 6:
                  extracted_rows.append({
                      "사업자": tokens[0],
                      "순번": tokens[1],
                      "사용유형": tokens[2],
                      "착신번호": tokens[3],
                      "통화시작시간": f"{tokens[4]} {tokens[5]}",
                      "사용시간(초)": tokens[6] if len(tokens) > 6 else "",
                      "발신기지국주소": (
                          " ".join(tokens[7:]) if len(tokens) > 7 else ""
                      ),
                  })

        if len(extracted_rows) > 0:
          df = pd.DataFrame(extracted_rows)
          st.success(
              f"2페이지에서 총 {len(df)}건의 표 데이터를 추출했습니다!"
          )

          st.write("### 2페이지 추출 결과 미리보기")
          st.dataframe(df)

          # 엑셀 다운로드
          output = io.BytesIO()
          with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="2페이지표")
          excel_data = output.getvalue()

          st.download_button(
              label="📥 2페이지 표 엑셀 다운로드 (.xlsx)",
              data=excel_data,
              file_name="page2_table_extracted.xlsx",
              mime=(
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              ),
          )
        else:
          st.warning(
              "2페이지에서 통화내역 표 패턴을 직접 감지하지 못했습니다."
              " (파일이 완전한 이미지 스캔본인 경우, 텍스트 레이어가 없어"
              " pypdf로 읽히지 않을 수 있습니다.)"
          )

  except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
