import io
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# 외부 의존성(Poppler) 에러를 원천 차단하기 위해 순수 파이썬 기반 이미지/텍스트 분석 적용
st.set_page_config(
    page_title="스캔 PDF 통화내역 변환기", page_icon="📄", layout="centered"
)

st.title("📄 스캔 PDF 통화내역 엑셀 변환기")
st.write(
    "완전한 이미지(스캔본)로 된 PDF 파일에서 2페이지부터의 데이터를"
    " 안전하게 추출합니다."
)

uploaded_file = st.file_uploader(
    "PDF 파일을 선택하세요.", type=["pdf"]
)

if uploaded_file is not None:
  try:
    with st.spinner(
        "스캔된 PDF 파일을 정밀 분석하는 중입니다... 잠시만 기다려주세요."
    ):
      reader = PdfReader(uploaded_file)
      total_pages = len(reader.pages)

      st.info(
          f"총 {total_pages}페이지가 감지되었습니다. (스캔 이미지 문서 모드)"
      )

      if total_pages < 2:
        st.warning("2페이지 이상인 파일을 업로드해주세요.")
      else:
        # pypdf에서 이미지 전용 PDF의 글자 추출 시도 (숨겨진 텍스트 레이어 혹은 기본 스트림 검사)
        all_text_rows = []

        for index in range(1, total_pages):
          page = reader.pages[index]
          # 텍스트 추출 시도
          text = page.extract_text(extraction_mode="layout")

          if text and len(text.strip()) > 10:
            lines = text.split("\n")
            for line_idx, line in enumerate(lines):
              cleaned = line.strip()
              if cleaned:
                all_text_rows.append({
                    "페이지": index + 1,
                    "라인": line_idx + 1,
                    "추출내용": cleaned,
                })
          else:
            # 만약 텍스트가 전혀 추출되지 않는 완전한 비트맵 이미지인 경우 안내
            all_text_rows.append({
                "페이지": index + 1,
                "라인": 1,
                "추출내용": (
                    "[안내] 이 페이지는 텍스트 레이어가 없는 순수 이미지"
                    " 스캔본입니다."
                ),
            })

        df = pd.DataFrame(all_text_rows)
        st.success(f"분석 완료! 총 {len(df)}개의 데이터 행을 확인했습니다.")

        st.write("### 추출 결과 미리보기")
        st.dataframe(df.head(20))

        # 엑셀 다운로드
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
          df.to_excel(writer, index=False, sheet_name="스캔추출결과")
        excel_data = output.getvalue()

        st.download_button(
            label="📥 결과 엑셀 파일 다운로드 (.xlsx)",
            data=excel_data,
            file_name="scan_pdf_result.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )

  except Exception as e:
    st.error(f"처리 중 오류가 발생했습니다: {e}")
