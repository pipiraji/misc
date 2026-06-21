#!/usr/bin/env python3
import os
import re
import argparse
import glob

# ==============================================================================
# 모듈 레벨 상수 / 정규식 (Pre-compiled)
# ==============================================================================
SPICE_EXTENSIONS = {".spi", ".sp", ".cdl", ".lib", ".inc", ".hsp", ".mod"}

SUBCKT_PATTERN = re.compile(r"^\.subckt\s+([\w.\-]+)(.*)", re.IGNORECASE | re.DOTALL)
PARAM_PATTERN = re.compile(r"\b([\w.\-]+)\s*=", re.IGNORECASE)
COMMENT_PATTERN = re.compile(r"\s\$|\s//")
QUOTE_PATTERN = re.compile(r"['\"][^'\"]*['\"]")


# ==============================================================================
# 파서
# ==============================================================================
def process_logical_line(logical_line, subckts_dict):
    """
    완성된 논리 라인 하나를 받아 .subckt 이면
    이름 / 핀(Terminals) / 파라미터를 추출한다.

    subckts_dict 구조:
        {
            subckt_name(소문자): {
                "pins":   [pin1, pin2, ...],   # 순서 보존
                "params": {param1, param2, ...}
            }
        }
    """
    if not logical_line.lower().startswith(".subckt"):
        return

    match = SUBCKT_PATTERN.match(logical_line.strip())
    if not match:
        return

    sub_name = match.group(1).lower()
    rest_of_line = match.group(2)

    # 따옴표 안 수식 제거 → param='val=1' 케이스에서 '=' 오인 방지
    rest_no_quotes = QUOTE_PATTERN.sub("", rest_of_line)

    # ── 핀 추출 ──────────────────────────────────────────────────
    # '=' 를 포함하지 않는 앞쪽 토큰들이 포트(핀)
    pins = []
    for token in rest_no_quotes.split():
        if "=" in token:
            break  # 파라미터 선언부 시작 → 핀 추출 종료
        pins.append(token.lower())

    # ── 파라미터 추출 ────────────────────────────────────────────
    params = {p.lower() for p in PARAM_PATTERN.findall(rest_no_quotes)}

    # ── dict 갱신 ────────────────────────────────────────────────
    if sub_name not in subckts_dict:
        subckts_dict[sub_name] = {"pins": [], "params": set()}

    # 핀은 처음 파싱한 것을 정(正)으로 사용 (중복 파일 대응)
    if not subckts_dict[sub_name]["pins"] and pins:
        subckts_dict[sub_name]["pins"] = pins

    subckts_dict[sub_name]["params"].update(params)


def parse_hspice_subckts_with_params(model_dir):
    """
    model_dir 하위 SPICE 파일을 재귀 탐색하여
    .subckt 선언부에서 이름·핀·파라미터를 추출한다.
    """
    subckts_dict = {}

    all_files = glob.glob(os.path.join(model_dir, "**", "*.*"), recursive=True)
    model_files = [
        p
        for p in all_files
        if os.path.isfile(p) and os.path.splitext(p)[1].lower() in SPICE_EXTENSIONS
    ]

    if not model_files:
        print(f"Warning: '{model_dir}' 에서 SPICE 파일을 찾을 수 없습니다.")
        print(f"  탐색 대상 확장자: {sorted(SPICE_EXTENSIONS)}")
        return subckts_dict

    print(f"Info: {len(model_files)}개 모델 파일 파싱 중...")

    for file_path in sorted(model_files):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            logical_line = None

            for raw_line in lines:
                line = raw_line.strip()

                # 빈 줄 / 전체 주석 라인 스킵
                if not line or line.startswith("*"):
                    continue

                # 인라인 주석 제거 (공백+$ 또는 공백+// 이후) → $var 변수명 보호
                line = COMMENT_PATTERN.split(line, maxsplit=1)[0].strip()
                if not line:
                    continue

                if line.startswith("+"):
                    # Continuation line → 이전 논리 라인에 이어붙임
                    if logical_line is not None:
                        logical_line += " " + line[1:].strip()
                else:
                    # 새 논리 라인 시작 전에 이전 라인 처리
                    if logical_line is not None:
                        process_logical_line(logical_line, subckts_dict)
                    logical_line = line

            # EOF: 마지막 논리 라인 처리
            if logical_line is not None:
                process_logical_line(logical_line, subckts_dict)

        except Exception as e:
            print(f"Warning: '{file_path}' 파싱 중 오류: {e}")

    return subckts_dict


# ==============================================================================
# 1. Calibre SVRF 생성
# ==============================================================================
def generate_svrf(subckts_dict, target_spi, ref_spi, top_cell, output_file):
    """Calibre NVN SVRF runset 생성"""
    lines = []

    lines.append(f"""\
// ==============================================================
// Auto-Generated Calibre NVN Runset
// ==============================================================

// --- 1. 입력 시스템 설정 ---
LAYOUT SYSTEM SPICE
LAYOUT PATH "{target_spi}"
LAYOUT PRIMARY "{top_cell}"

SOURCE SYSTEM SPICE
SOURCE PATH "{ref_spi}"
SOURCE PRIMARY "{top_cell}"

// --- 2. 매칭 옵션 ---
// 1:1 SPICE-to-SPICE 완전 비교 플로우.
// 게이트 인식/전원망 선언 불필요 — 넷리스트 위상 그대로 비교.
LVS INJECT LOGIC YES
LVS RECOGNIZE GATES NONE
LVS COMPARE CASE NO
LVS CHECK PORT NAMES YES

// --- 3. 리포트 설정 ---
// 목적: 불일치(디바이스 수, 넷, 파라미터) 전량 출력 + 최대 가독성
//
// BX  : BOX 처리된 셀 목록을 setup 섹션에 출력 → BOX 적용 확인용
// FX  : DETAILED ERROR ANALYSIS 섹션 활성화 → 오류 원인 한눈에 파악
// G   : Property Error 불일치 시 인스턴스 연결 상세 출력 → 파라미터 오류 디버깅
// D   : Missing Instance/Gate 불일치 시 인스턴스 연결 상세 출력 → 디바이스 수 미스매치
// NP  : 정상 매칭된 핀은 report에서 생략 → 오류 핀만 집중 표시
// NE  : 디바이스 인스턴스 수 미스매치 시 NOT COMPARED로 즉시 표시
// RA  : Ambiguity resolution 포인트 출력 억제 → report 노이즈 제거
LVS REPORT "lvs_compare.rep"
LVS REPORT OPTION BX FX G D NP NE RA

// --- 4. 기생 성분 필터링 ---
// PEX 넷리스트의 기생 C → OPEN, 기생 R → SHORT 처리하여 넷 병합.
LVS FILTER C OPEN
LVS FILTER R SHORT

// --- 5. LVS BOX 선언 ---
""")

    for sub_name in sorted(subckts_dict.keys()):
        lines.append(f"LVS BOX {sub_name}\n")

    lines.append("\n// --- 6. Trace Properties ---\n")
    for sub_name in sorted(subckts_dict.keys()):
        params = sorted(subckts_dict[sub_name]["params"])
        if params:
            lines.append(f"\n// [{sub_name}]\n")
            for param in params:
                # SVRF TRACE PROPERTY: 쌍따옴표로 예약어 충돌 방지
                lines.append(f'TRACE PROPERTY {sub_name} "{param}" "{param}" 0\n')

    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"  [O] Calibre SVRF : '{output_file}'")


# ==============================================================================
# 2. IC Validator RS 생성
# ==============================================================================
def generate_icv_rs(subckts_dict, target_spi, ref_spi, top_cell, output_file):
    """IC Validator NVN runset 생성"""
    lines = []

    # ── 헤더 / 초기화 ────────────────────────────────────────────────────────
    # 매뉴얼 문법:
    #   read_layout_netlist(layout_file   = {{filename = "...", format = SPICE}})
    #   schematic(          schematic_file = {{filename = "...", format = SPICE}})
    lines.append(f"""\
// ==============================================================
// Auto-Generated IC Validator NVN Runset
// ==============================================================
#include <icv.rh>

lay = read_layout_netlist(
    layout_file = {{{{filename = "{target_spi}", format = SPICE}}}}
);

sch = schematic(
    schematic_file = {{{{filename = "{ref_spi}", format = SPICE}}}}
);

compare_state = init_compare_matrix(
    netlist_vs_netlist = PARTIAL_RUNSET
);

// --- 기생 성분 필터링 ---
filter(compare_state, CAPACITOR, {{"*"}}, filter_options(filter_type = FILTER_OPEN));
filter(compare_state, RESISTOR,  {{"*"}}, filter_options(filter_type = FILTER_SHORT));

// --- map_gendev: GENERIC device 매핑 (terminals 필수) ---
// 매뉴얼: map_gendev(state, device_name="...", terminals={{{{pin_name="...", pin_compared=true}}, ...}})
""")

    # ── map_gendev ────────────────────────────────────────────────────────────
    for sub_name in sorted(subckts_dict.keys()):
        pins = subckts_dict[sub_name]["pins"]

        if pins:
            terminals_str = ", ".join(
                f'{{pin_name = "{pin}", pin_compared = true}}' for pin in pins
            )
            lines.append(
                f"map_gendev(compare_state,\n"
                f'    device_name = "{sub_name}",\n'
                f"    terminals   = {{{terminals_str}}}\n"
                f");\n\n"
            )
        else:
            # 핀 정보 없는 예외 케이스 — 경고 주석 포함
            lines.append(
                f'// WARNING: "{sub_name}" 핀 정보 없음 — terminals 수동 확인 필요\n'
                f"map_gendev(compare_state,\n"
                f'    device_name = "{sub_name}",\n'
                f"    terminals   = {{}}\n"
                f");\n\n"
            )

    # ── check_property ────────────────────────────────────────────────────────
    # 매뉴얼 문법:
    #   check_property(state, device_type, device_names, property_tolerances = ...)
    #   device_names    → {"string", ...}   단일 중괄호
    #   property_tolerances → {{"prop", [lo, hi]}, ...}  이중 중괄호
    lines.append("// --- check_property: 파라미터 허용 오차 0 (완전 일치) ---\n")
    for sub_name in sorted(subckts_dict.keys()):
        params = sorted(subckts_dict[sub_name]["params"])
        if not params:
            continue

        tol_str = ", ".join(f'{{"{p}", [0, 0], ABSOLUTE}}' for p in params)
        lines.append(
            f'check_property(compare_state, GENERIC, {{"{sub_name}"}},\n'
            f"    property_tolerances = {{{tol_str}}}\n"
            f");\n\n"
        )

    # ── compare ───────────────────────────────────────────────────────────────
    lines.append(f"""\
compare(compare_state, sch, lay,
    schematic_top_cell = "{top_cell}",
    layout_top_cell    = "{top_cell}"
);
""")

    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"  [O] IC Validator  : '{output_file}'")


# ==============================================================================
# Main
# ==============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PDK Subckt 기반 Calibre/ICV 통합 NVN 런셋 생성기",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-m", "--model_dir", required=True, help="HSPICE 모델 디렉토리 (하위 재귀 탐색)"
    )
    parser.add_argument(
        "-s1",
        "--spice1",
        required=True,
        help="Target Netlist  (SPF/DSPF 등 레이아웃 추출)",
    )
    parser.add_argument(
        "-s2", "--spice2", required=True, help="Reference Netlist (Schematic 기반)"
    )
    parser.add_argument(
        "-t",
        "--top_cell",
        required=True,
        help="최상위 Subckt 이름 (BOX/GENDEV 목록에서 자동 제외)",
    )
    parser.add_argument(
        "-o_svrf", default="run_nvn.svrf", help="출력 SVRF 파일명 (기본: run_nvn.svrf)"
    )
    parser.add_argument(
        "-o_icv", default="run_nvn.rs", help="출력 ICV  파일명 (기본: run_nvn.rs)"
    )

    args = parser.parse_args()

    # 단 1회 파싱으로 Calibre·ICV 양쪽에 공유
    subckts_data = parse_hspice_subckts_with_params(args.model_dir)

    if not subckts_data:
        print("Error: 파싱된 데이터가 없습니다. 실행을 중단합니다.")
        raise SystemExit(1)

    removed = subckts_data.pop(args.top_cell.lower(), None)
    if removed is not None:
        print(f"Info: 최상위 셀 '{args.top_cell}' 을 BOX/GENDEV 목록에서 제외했습니다.")

    print("\n[런셋 생성 결과]")
    generate_svrf(subckts_data, args.spice1, args.spice2, args.top_cell, args.o_svrf)
    generate_icv_rs(subckts_data, args.spice1, args.spice2, args.top_cell, args.o_icv)

    total_pins = sum(len(v["pins"]) for v in subckts_data.values())
    total_params = sum(len(v["params"]) for v in subckts_data.values())
    print(
        f"\n완료!  매크로 {len(subckts_data)}개  |  핀 {total_pins}개  |  파라미터 {total_params}개"
    )
