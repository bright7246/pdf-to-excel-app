import io
import re
import pandas as pd
from pypdf import PdfReader
import streamlit as st

st.set_page_config(
    page_title="통화내역 PDF to Excel 변환기", page_icon="📞", layout="centered"
)

st.title("📞 통화내역 PDF ➔ 엑셀 변환기 (2페이지 이후 전체)")
st.write(
    "3페이지부터 컬럼 제목 없이 내용만 이어지는 문서도 완벽하게 하나의 엑셀로"
    " 통합해 드립니다."
)

# 파일 업로드
uploaded_file = st.file_uploader(
    "PDF 파일을 선택하세요.", type=["pdf"]
)

if uploaded_file is not None:
  try:
    reader = PdfReader(uploaded_file)
    total_pages = len(reader.pages)

    st.info(f"총 페이지 수: {total_pages}페이지")

    if total_pages < 2:
      st.warning(
          "업로드하신 PDF는 1페이지밖에 없습니다. 2페이지 이상인 파일을"
          " 업로드해주세요."
      )
    else:
      with st.spinner(
          "2페이지부터 끝까지 데이터를 일괄 수집하고 정제하는 중입니다..."
      ):
        all_rows = []

        # 2페이지부터 끝까지 전체 페이지 순회
        for index in range(1, total_pages):
          page = reader.pages[index]
          text = page.extract_text()

          if text:
            lines = text.split("\n")
            for line in lines:
              line_str = line.strip()
              
              # 통신사 이름으로 시작하는 데이터 행 패턴 감지 (LGU+, SKT, KT 등)
              if any(line_str.startswith(telecom) for telecom in ["LGU+", "SKT", "KT", "LGU", "SK", "LG"]):
                # 공백 기준으로 데이터 분리
                parts = re.split(r'\s{2,}', line_str)
                
                if len(parts) >= 6:
                  row_data = {
                      "사업자": parts[0] if len(parts) > 0 else "",
                      "순번": parts[1] if len(parts) > 1 else "",
                      "사용유형": parts[2] if len(parts) > 2 else "",
                      "착신번호": parts[3] if len(parts) > 3 else "",
                      "통화시작시간": parts[4] if len(parts) > 4 else "",
                      "사용시간(초)": parts[5] if len(parts) > 5 else "",
                      "발신기지국주소": parts[6] if len(parts) > 6 else ""
                  }
                  all_rows.append(row_data)
                else:
                  # 단일 공백 기준으로 유연하게 분리 시도
                  simple_parts = line_str.split()
                  if len(simple_parts) >= 6:
                    row_data = {
                        "사업자": simple_parts[0],
                        "순번": simple_parts[1],
                        "사용유형": simple_parts[2],
                        "착신번호": simple_parts[3],
                        "통화시작시간": f"{simple_parts[4]} {simple_parts[5]}" if len(simple_parts) > 5 else "",
                        "사용시간(초)": simple_parts[6] if len(simple_parts) > 6 else "",
                        "발신기지국주소": " ".join(simple_parts[7:]) if len(simple_parts) > 7 else ""
                    }
                    all_rows.append(row_data)

        if len(all_rows) > 0:
          df = pd.DataFrame(all_rows)
          st.success(f"총 {len(df)}건의 통화내역 데이터를 누락 없이 추출했습니다!")
          
          st.write("### 추출된 데이터 미리보기 (상위 10행)")
          st.dataframe(df.head(10))

          # 엑셀 파일 바이너리 생성
          output = io.BytesIO()
          with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="통화내역통합")
          excel_data = output.getvalue()

          st.download_button(
              label="📥 통합된 엑셀 파일 다운로드 (.xlsx)",
              data=excel_data,
              file_name="call_history_all_pages.xlsx",
              mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          )
        else:
          st.warning(
              "데이터 패턴을 찾지 못했습니다. PDF가 텍스트를 포함하고 있는지 확인해 주세요."
          )

  except Exception as e:
    st.error(f"파일을 처리하는 중 오류가 발생했습니다: {e}")
