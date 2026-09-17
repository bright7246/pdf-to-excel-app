import io
import pandas as pd
from pdf2image import convert_from_bytes
import pytesseract
from pypdf import PdfReader
import streamlit as st

st.set_page_config(
    page_title="통화내역 OCR 완벽 변환기", page_icon="🔍", layout="centered"
)

st.title("🔍 통화내역 이미지 PDF ➔ 엑셀 완벽 변환기 (OCR)")
st.write(
    "그림(스캔) 형태로 된 PDF 파일도 OCR(문자 인식) 기술을 통해 2페이지부터"
    " 끝까지 통화내역을 정확하게 읽어와 엑셀로 만들어 드립니다."
)

# 파일 업로드
uploaded_file = st.file_uploader(
    "PDF 파일을 선택하세요.", type=["pdf"]
)

if uploaded_file is not None:
  try:
    with st.spinner(
        "PDF를 고화질 이미지로 변환하고 OCR 문자 인식을 수행하는 중입니다..."
        " (페이지 수에 따라 1~2분 정도 소요될 수 있습니다)"
    ):
      # PDF 파일을 바이트로 읽기
      pdf_bytes = uploaded_file.read()

      # 전체 페이지를 이미지로 변환 (dpi를 높여서 글자가 선명하게 보이도록 설정)
      images = convert_from_bytes(pdf_bytes, dpi=200)
      total_pages = len(images)

      st.info(f"총 {total_pages}페이지가 감지되었습니다.")

      if total_pages < 2:
        st.warning(
            "업로드하신 PDF는 1페이지밖에 없습니다. 2페이지 이상인 파일을"
            " 업로드해주세요."
        )
      else:
        all_extracted_rows = []

        # 2페이지부터 끝까지 순회 (인덱스 1부터 시작)
        for index in range(1, total_pages):
          img = images[index]

          # pytesseract를 이용해 한국어 + 영어 텍스트 추출
          ocr_text = pytesseract.image_to_string(img, lang="kor+eng")

          # 줄 단위로 분리
          lines = ocr_text.split("\n")
          for line in lines:
            line_str = line.strip()

            if line_str:
              # 머리글이나 불필요한 안내 문구는 제외하고 실제 데이터나 의미 있는 줄만 수집
              if not any(
                  keyword in line_str
                  for keyword in ["개인정보유출주의", "다운로드일시", "발신지 통화내역"]
              ):
                all_extracted_rows.append({
                    "페이지": index + 1,
                    "추출된 통화내역 내용": line_str,
                })

        if len(all_extracted_rows) > 0:
          df = pd.DataFrame(all_extracted_rows)
          st.success(
              f"OCR 분석 완료! 총 {len(df)}줄의 데이터를 추출했습니다."
          )

          st.write("### 추출된 데이터 미리보기 (상위 15행)")
          st.dataframe(df.head(15))

          # 엑셀 파일 바이너리 생성
          output = io.BytesIO()
          with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="통화내역OCR")
          excel_data = output.getvalue()

          st.download_button(
              label="📥 OCR 변환된 엑셀 파일 다운로드 (.xlsx)",
              data=excel_data,
              file_name="ocr_call_history.xlsx",
              mime=(
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              ),
          )
        else:
          st.warning(
              "추출된 텍스트가 없습니다. 이미지 화질이 너무 낮거나 파일에"
              " 문제가 있는지 확인해 주세요."
          )

  except Exception as e:
    st.error(
        "처리 중 오류가 발생했습니다. (Tesseract 패키지 설정에 시간이 걸릴"
        f" 수 있습니다) 오류 내용: {e}"
    )
