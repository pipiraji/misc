import os
import tarfile
import gzip
import zlib


class LamaFile:
    def __init__(self, *args, **kwargs):
        pass

    def is_tgz_under_limit(self, target_path, limit_mb=750):
        """
        타겟 경로를 tar.gz로 가상 압축하며 용량 제한을 체크합니다.
        제한 초과 시 False, 안전하면 최종 압축 크기(bytes)를 반환합니다.

        Note:
            실시간 용량 체크를 위해 zlib.Z_SYNC_FLUSH를 사용하므로,
            반환되는 바이트 수는 실제 tar.gz 생성 시보다 보수적으로(크게) 측정됩니다.
            정밀한 크기 측정이 아닌 '제한 초과 여부 사전 검증' 용도로 사용하십시오.
        """
        limit_bytes = limit_mb * 1024 * 1024

        class _ByteCounter:
            """gzip fileobj 인터페이스를 구현하는 바이트 카운터."""

            __slots__ = ("count",)

            def __init__(self):
                self.count = 0

            def write(self, b: bytes) -> int:
                self.count += len(b)
                return len(b)

            def flush(self):
                pass  # gzip이 요구하는 인터페이스 충족용

        def _iter_files(path):
            """압축 대상 (full_path, arcname) 쌍을 지연 생성하여 메모리를 절약합니다."""
            if os.path.isfile(path):
                yield path, os.path.basename(path)
            elif os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    dirs[:] = [
                        d for d in dirs if not os.path.islink(os.path.join(root, d))
                    ]
                    if ".ipynb_checkpoints" in root:
                        continue
                    for file in sorted(files):
                        full_path = os.path.join(root, file)
                        yield full_path, os.path.relpath(full_path, path)
            else:
                raise FileNotFoundError(f"경로를 찾을 수 없습니다: {path}")

        counter = _ByteCounter()
        gz = None
        tar = None

        try:
            gz = gzip.GzipFile(fileobj=counter, mode="wb")
            tar = tarfile.open(fileobj=gz, mode="w|")

            # ── 1. 가상 압축 & 실시간 용량 체크 (제너레이터 활용) ───────────────
            for file_path, arcname in _iter_files(target_path):
                tar.add(file_path, arcname=arcname)
                gz.flush(zlib.Z_SYNC_FLUSH)
                if counter.count > limit_bytes:
                    return False

            # ── 2. 정상 마감 ──────────────────────────────────────────────────
            tar.close()
            gz.close()

            return False if counter.count > limit_bytes else counter.count

        finally:
            # ── 3. 명시적 자원 해제 (비공식 API 의존성 제거, EAFP 패턴) ──────────
            if tar is not None:
                try:
                    tar.close()
                except Exception:
                    pass

            if gz is not None:
                try:
                    gz.close()
                except Exception:
                    pass
