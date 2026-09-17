import io
import pandas as pd
import pdfplumber
import streamlit as st

st.set_page_config(
    page_title="통화내역 PDF to Excel 변환기", page_icon="📞", layout="centered"
)

st.title("📞 통화내역 PDF ➔ 엑셀 변환기 (2페이지 이후 전체)")
st.write(
    "2페이지부터 끝까지 표 구조를 정밀하게 분석하여 엑셀로 통합해 드립니다."
)

# 파일 업로드
uploaded_file = st.file_uploader(
    "PDF 파일을 선택하세요.", type=["pdf"]
)

if uploaded_file is not None:
  try:
    with st.spinner(
        "PDF 파일을 분석하고 표 데이터를 추출하는 중입니다..."
    ):
      all_rows = []
      header_row = None

      # pdfplumber를 사용하여 페이지별 표(Table) 구조 직접 추출
      with pdfplumber.open(uploaded_file) as pdf:
        total_pages = len(pdf.pages)
        st.info(f"총 페이지 수: {total_pages}페이지")

        if total_pages < 2:
          st.warning(
              "업로드하신 PDF는 1페이지밖에 없습니다. 2페이지 이상인 파일을"
              " 업로드해주세요."
          )
        else:
          # 2페이지부터 끝까지 순회 (인덱스 1부터 시작)
          for index in range(1, total_pages):
            page = pdf.pages[index]
            tables = page.extract_tables()

            for table in tables:
              for row_idx, row in enumerate(table):
                # 불필요한 빈 칸 제거
                cleaned_row = [
                    cell.strip().replace("\n", " ") if cell else ""
                    for cell in row
                ]

                # 첫 번째 페이지(2페이지)의 첫 행은 보통 컬럼 헤더(사업자, 순번 등)
                if index == 1 and row_idx == 0 and not header_row:
                  header_row = cleaned_row
                  continue

                # 데이터 행이 비어있지 않고, 실제 통신사 데이터나 번호가 포함된 경우 수집
                if any(cleaned_row):
                  # 헤더 개수와 데이터 개수가 맞지 않아도 유연하게 수집
                  all_rows.append(cleaned_row)

      if len(all_rows) > 0:
        # 헤더가 감지된 경우 헤더 적용, 아니면 기본 컬럼명 부여
        if header_row and len(header_row) >= 6:
          df = pd.DataFrame(all_rows, columns=header_row[: len(all_rows[0])])
        else:
          # 기본 컬럼 구조 지정
          cols = [
              "사업자",
              "순번",
              "사용유형",
              "착신번호",
              "통화시작시간",
              "사용시간(초)",
              "발신기지국주소",
          ]
          # 컬럼 수 맞추기
          if len(all_rows[0]) == len(cols):
            df = pd.DataFrame(all_rows, columns=cols)
          else:
            df = pd.DataFrame(all_rows)

        st.success(
            f"총 {len(df)}건의 통화내역 데이터를 성공적으로 추출했습니다!"
        )

        st.write("### 추출된 데이터 미리보기 (상위 10행)")
        st.dataframe(df.head(10))

        # 엑셀 파일 바이너리 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
          df.to_excel(writer, index=False, sheet_name="통화내역")
        excel_data = output.getvalue()

        st.download_button(
            label="📥 정제된 엑셀 파일 다운로드 (.xlsx)",
            data=excel_data,
            file_name="call_history_table.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
      else:
        st.warning(
            "표 데이터를 찾지 못했습니다. PDF가 올바른 문서인지 확인해 주세요."
        )

  except Exception as e:
    st.error(f"파일을 처리하는 중 오류가 발생했습니다: {e}")
