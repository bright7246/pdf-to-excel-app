import io
import re
import pandas as pd
from pdf2image import convert_from_bytes
import pytesseract
import streamlit as st

st.set_page_config(
    page_title="통화내역 순번 완벽 정렬기", page_icon="📞", layout="centered"
)

st.title("📞 통화내역 순번 완벽 고정 & 정제 변환기")
st.write(
    "순번이 누락되거나 밀리지 않도록 1번부터 마지막 번호까지 완벽한 연속성을"
    " 유지하며 각 줄의 데이터를 정확한 칸에 매칭합니다."
)

uploaded_file = st.file_uploader(
    "PDF 파일을 선택하세요.", type=["pdf"]
)

if uploaded_file is not None:
  try:
    with st.spinner(
        "스캔본 이미지를 OCR 분석하고 순번 연속성을 엄격하게 맞추는 중입니다..."
    ):
      pdf_bytes = uploaded_file.read()
      images = convert_from_bytes(pdf_bytes, dpi=200)
      total_pages = len(images)

      st.info(f"총 {total_pages}페이지 분석 중...")

      if total_pages < 2:
        st.warning("2페이지 이상인 파일을 업로드해주세요.")
      else:
        all_raw_lines = []

        # 정규식 패턴 정의
        phone_pattern = re.compile(r'\d{2,3}-\S*-\d{4}')
        datetime_pattern = re.compile(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}')
        time_pattern = re.compile(r'\d{2}:\d{2}:\d{2}')

        # 2페이지부터 끝까지 순회 (인덱스 1부터 시작)
        for index in range(1, total_pages):
          img = images[index]
          ocr_text = pytesseract.image_to_string(img, lang="kor+eng")

          lines = ocr_text.split("\n")
          for line in lines:
            line_str = line.strip()
            if not line_str:
              continue

            # 상단 머리글 필터링
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

            all_raw_lines.append((index + 1, line_str))

        parsed_rows = []
        expected_seq = 1  # 1번부터 강제로 순번 추적 시작

        for page_no, line_str in all_raw_lines:
          # OCR 오타 정돈 및 구분자 정리
          cleaned = (
              line_str.replace("ucu+", "LGU+")
              .replace("tcu+", "LGU+")
              .replace("ucu", "LGU+")
              .replace("tcu", "LGU+")
              .replace("|", " ")
          )

          tokens = cleaned.split()
          if len(tokens) < 4:
            continue

          # 전화번호나 날짜가 포함된 '유효한 통화내역 행'인지 우선 검증
          has_phone = bool(phone_pattern.search(cleaned))
          has_time = bool(datetime_pattern.search(cleaned)) or bool(
              time_pattern.search(cleaned)
          )

          if has_phone or has_time:
            # 사업자 추출
            business = "LGU+"
            for t in tokens[:3]:
              if any(
                  tel in t.upper() for tel in ["LGU", "SKT", "KT", "LG", "SK"]
              ):
                business = "LGU+" if "LG" in t.upper() else t
                break

            # 순번 찾기 시도 (토큰 중 숫자가 있으면 확인)
            found_seq = None
            for t in tokens[:4]:
              if t.isdigit():
                val = int(t)
                # 현재 예상되는 순번 전후 범위 내에 있다면 인정
                if abs(val - expected_seq) <= 3:
                  found_seq = val
                  break

            # OCR이 순번을 놓쳤거나 오인식한 경우, '예상되는 순번(expected_seq)'을 강제로 부여하여 밀림 방지
            if found_seq and found_seq >= expected_seq:
              current_seq = found_seq
              expected_seq = found_seq + 1
            else:
              current_seq = expected_seq
              expected_seq += 1

            # 사용유형 추출 (3G, VOLTE음성 등)
            usage_type = "VOLTE음성"
            for t in tokens:
              if (
                  "3G" in t
                  .upper()
                  or "VOLTE" in t.upper()
                  or "LTE" in t.upper()
                  or "음성" in t
                  or "문자" in t
              ):
                usage_type = t
                break

            # 착신번호 추출
            phone_match = phone_pattern.search(cleaned)
            phone = phone_match.group(0) if phone_match else ""

            # 통화시작시간 추출
            dt_match = datetime_pattern.search(cleaned)
            start_time = dt_match.group(0) if dt_match else ""

            # 사용시간 추출
            time_matches = time_pattern.findall(cleaned)
            duration = ""
            if len(time_matches) >= 2:
              duration = time_matches[1]
            elif len(time_matches) == 1 and not start_time:
              duration = time_matches[0]

            # 발신기지국주소 추출
            address = ""
            if dt_match:
              dt_end_idx = cleaned.find(start_time) + len(start_time)
              residual = cleaned[dt_end_idx:].strip()
              if residual:
                if duration and residual.startswith(duration):
                  residual = residual[len(duration) :].strip()
                address = residual.lstrip("|- ").strip()

            # 데이터 추가 (순번이 비어있지 않고 번호가 있는 경우)
            if phone:
              parsed_rows.append({
                  "페이지": page_no,
                  "사업자": business,
                  "순번": current_seq,
                  "사용유형": usage_type,
                  "착신번호": phone,
                  "통화시작시간": start_time,
                  "사용시간(초)": duration,
                  "발신기지국주소": address,
              })

        if len(parsed_rows) > 0:
          df = pd.DataFrame(parsed_rows)
          # 중복 순번 제거 및 오름차순 정렬
          df = df.drop_duplicates(subset=["순번"]).sort_values(by="순번").reset_index(drop=True)

          st.success(
              f"순번 연속성 보정 완료! 총 {len(df)}건의 데이터가 정확하게"
              " 정렬되었습니다."
          )

          st.write("### 정돈된 표 데이터 미리보기")
          st.dataframe(df.head(15))

          # 엑셀 파일 생성
          output = io.BytesIO()
          with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="순번정렬통화내역")
          excel_data = output.getvalue()

          st.download_button(
              label="📥 완벽 정렬된 엑셀 파일 다운로드 (.xlsx)",
              data=excel_data,
              file_name="strict_sequenced_call_history.xlsx",
              mime=(
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              ),
          )
        else:
          st.warning("데이터 행을 추출하지 못했습니다.")

  except Exception as e:
    st.error(f"처리 중 오류 발생: {e}")
