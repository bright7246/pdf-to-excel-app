import io
import re
import pandas as pd
from pdf2image import convert_from_bytes
import pytesseract
import streamlit as st

st.set_page_config(
    page_title="통화내역 OCR 정제 변환기", page_icon="📞", layout="centered"
)

st.title("📞 통화내역 OCR ➔ 표 형식 엑셀 변환기")
st.write(
    "스캔본 PDF에서 통화내역 표 데이터만 정확히 발라내어 사업자, 순번, 착신번호"
    " 등 항목별로 깔끔하게 정돈된 엑셀을 만들어 드립니다."
)

uploaded_file = st.file_uploader(
    "PDF 파일을 선택하세요.", type=["pdf"]
)

if uploaded_file is not None:
  try:
    with st.spinner(
        "PDF를 고화질로 읽어내어 통화내역 행을 정밀 파싱하는 중입니다..."
    ):
      pdf_bytes = uploaded_file.read()
      images = convert_from_bytes(pdf_bytes, dpi=200)
      total_pages = len(images)

      st.info(f"총 {total_pages}페이지 분석 중...")

      if total_pages < 2:
        st.warning("2페이지 이상인 파일을 업로드해주세요.")
      else:
        parsed_rows = []

        # 2페이지부터 끝까지 순회 (인덱스 1부터 시작)
        for index in range(1, total_pages):
          img = images[index]
          ocr_text = pytesseract.image_to_string(img, lang="kor+eng")

          lines = ocr_text.split("\n")
          for line in lines:
            line_str = line.strip()

            if not line_str:
              continue

            # 불필요한 머리글 및 안내 문구 제거
            if any(
                kw in line_str
                for kw in [
                    "개인정보유출주의",
                    "다운로드일시",
                    "발신지 통화내역",
                    "접수번호",
                    "전화번호",
                    "조회기간",
                    "전체건수",
                ]
            ):
              continue

            # OCR 인식 오타 보정 (예: ucu+, tcu+ -> LGU+)
            cleaned_line = (
                line_str.replace("ucu+", "LGU+")
                .replace("tcu+", "LGU+")
                .replace("ucu", "LGU+")
                .replace("tcu", "LGU+")
            )

            # 핵심 조건: 줄 안에 순번(숫자)과 날짜/전화번호 패턴이 함께 포함된 통화내역 행만 타겟팅
            # 통화내역은 보통 [사업자] [순번(숫자)] 형태로 시작함
            tokens = cleaned_line.split()

            if len(tokens) >= 4:
              # 두 번째나 세 번째 토큰이 순번(숫자) 형태인지 확인
              possible_seq = None
              seq_idx = -1

              for i, token in enumerate(tokens[:3]):
                # 순번은 1~4자리 숫자
                if token.isdigit() and 1 <= int(token) <= 5000:
                  possible_seq = token
                  seq_idx = i
                  break

              if possible_seq and seq_idx >= 0:
                # 순번이 발견되었다면 그 앞은 사업자, 뒤부터는 사용유형, 번호, 시간 등으로 배치
                business = (
                    " ".join(tokens[:seq_idx])
                    if seq_idx > 0
                    else "LGU+"
                )
                # 오타나 깨진 사업자 정돈
                if not any(
                    tel in business for tel in ["LGU+", "SKT", "KT", "LG"]
                ):
                  business = "LGU+"

                seq = possible_seq
                remaining = tokens[seq_idx + 1 :]

                usage_type = remaining[0] if len(remaining) > 0 else ""
                target_num = remaining[1] if len(remaining) > 1 else ""

                # 시간 정보 및 주소 조합 탐색
                rest_text = " ".join(remaining[2:]) if len(remaining) > 2 else ""

                parsed_rows.append({
                    "페이지": index + 1,
                    "사업자": business,
                    "순번": seq,
                    "사용유형": usage_type,
                    "착신번호": target_num,
                    "상세내용및시간/주소": rest_text,
                })

        if len(parsed_rows) > 0:
          df = pd.DataFrame(parsed_rows)
          st.success(
              f"정밀 파싱 완료! 총 {len(df)}건의 통화내역 행을 추출했습니다."
          )

          st.write("### 정제된 데이터 미리보기")
          st.dataframe(df.head(15))

          # 엑셀 다운로드 생성
          output = io.BytesIO()
          with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="정제된통화내역")
          excel_data = output.getvalue()

          st.download_button(
              label="📥 정돈된 엑셀 파일 다운로드 (.xlsx)",
              data=excel_data,
              file_name="cleaned_call_history.xlsx",
              mime=(
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              ),
          )
        else:
          st.warning(
              "표 형식의 데이터 행을 명확히 분리하지 못했습니다. OCR 인식"
              " 상태를 점검 중입니다."
          )

  except Exception as e:
    st.error(f"처리 중 오류 발생: {e}")
