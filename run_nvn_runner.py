#!/usr/bin/env python3
"""
간단 실행기: `nvn.py`를 호출해 기본 테스트 입력으로 런셋 파일을 생성합니다.

기본 동작:
  - model_dir: ./models
  - spice1:    ./test_inputs/target.sp
  - spice2:    ./test_inputs/reference.sp
  - top_cell:  TOP

사용법 예:
  python run_nvn_runner.py
  python run_nvn_runner.py --model_dir my_models --spice1 a.sp --spice2 b.sp --top_cell TOP -o_svrf out.svrf -o_icv out.rs
"""

import sys
import subprocess
import argparse
import os


def main():
    parser = argparse.ArgumentParser(
        description="Run nvn.py with sane defaults for this repo"
    )
    parser.add_argument(
        "--model_dir",
        default=os.path.join("test_inputs", "models"),
        help="HSPICE model directory",
    )
    parser.add_argument(
        "--spice1",
        default=os.path.join("test_inputs", "target.sp"),
        help="Target netlist path",
    )
    parser.add_argument(
        "--spice2",
        default=os.path.join("test_inputs", "reference.sp"),
        help="Reference netlist path",
    )
    parser.add_argument("--top_cell", default="TOP", help="Top cell name")
    parser.add_argument("-o_svrf", default="run_nvn.svrf", help="Output SVRF filename")
    parser.add_argument("-o_icv", default="run_nvn.rs", help="Output ICV filename")
    args = parser.parse_args()

    nvn_script = os.path.join(os.path.dirname(__file__), "nvn.py")
    if not os.path.exists(nvn_script):
        print(f"Error: nvn.py를 찾을 수 없습니다: {nvn_script}")
        return 2

    cmd = [
        sys.executable,
        nvn_script,
        "-m",
        args.model_dir,
        "-s1",
        args.spice1,
        "-s2",
        args.spice2,
        "-t",
        args.top_cell,
        "-o_svrf",
        args.o_svrf,
        "-o_icv",
        args.o_icv,
    ]

    print("Running:", " ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"nvn.py 실행 실패: {e}")
        return e.returncode

    print("완료: 출력 파일을 확인하세요:")
    print("  -", args.o_svrf)
    print("  -", args.o_icv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
