import io
import pandas as pd
from pdf2image import convert_from_bytes
import pytesseract
import streamlit as st

st.set_page_config(
    page_title="스캔 PDF 통화내역 OCR 변환기", page_icon="📞", layout="centered"
)

st.title("📞 스캔 PDF 통화내역 ➔ 엑셀 완벽 변환기")
st.write(
    "순수 이미지(스캔본)로 된 PDF 파일도 OCR(인공지능 문자 인식)을 통해"
    " 2페이지부터의 표 내용을 완벽하게 읽어와 엑셀로 변환해 드립니다."
)

uploaded_file = st.file_uploader(
    "PDF 파일을 선택하세요.", type=["pdf"]
)

if uploaded_file is not None:
  try:
    with st.spinner(
        "스캔된 PDF를 고화질 이미지로 변환하고 OCR 분석을 수행 중입니다... (약"
        " 30초~1분 소요)"
    ):
      pdf_bytes = uploaded_file.read()

      # 시스템에 설치된 poppler를 이용해 PDF를 고화질 이미지로 변환
      images = convert_from_bytes(pdf_bytes, dpi=200)
      total_pages = len(images)

      st.info(f"총 {total_pages}페이지가 감지되었습니다. (OCR 분석 모드)")

      if total_pages < 2:
        st.warning("2페이지 이상인 파일을 업로드해주세요.")
      else:
        extracted_rows = []

        # 2페이지부터 끝까지 순회 (인덱스 1부터 시작)
        for index in range(1, total_pages):
          img = images[index]

          # tesseract를 이용해 한국어 + 영어 텍스트 추출
          ocr_text = pytesseract.image_to_string(img, lang="kor+eng")

          lines = ocr_text.split("\n")
          for line in lines:
            line_str = line.strip()

            if line_str:
              # 상단 머리글 등 불필요한 문구 제외
              if not any(
                  kw in line_str
                  for kw in [
                      "개인정보유출주의",
                      "다운로드일시",
                      "발신지 통화내역",
                  ]
              ):
                extracted_rows.append({
                    "페이지": index + 1,
                    "추출된 통화내역": line_str,
                })

        if len(extracted_rows) > 0:
          df = pd.DataFrame(extracted_rows)
          st.success(
              f"OCR 분석 성공! 총 {len(df)}줄의 데이터를 추출했습니다."
          )

          st.write("### 추출된 데이터 미리보기 (상위 15행)")
          st.dataframe(df.head(15))

          # 엑셀 다운로드 생성
          output = io.BytesIO()
          with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="통화내역OCR")
          excel_data = output.getvalue()

          st.download_button(
              label="📥 변환된 엑셀 파일 다운로드 (.xlsx)",
              data=excel_data,
              file_name="ocr_call_history.xlsx",
              mime=(
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              ),
          )
        else:
          st.warning(
              "텍스트를 추출하지 못했습니다. 이미지 화질이나 파일 상태를"
              " 확인해 주세요."
          )

  except Exception as e:
    st.error(
        "처리 중 오류가 발생했습니다. (packages.txt 설정이 정상적으로"
        f" 반영되었는지 확인해 주세요) 오류 내용: {e}"
    )
