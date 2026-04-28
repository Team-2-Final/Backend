from __future__ import annotations

import random
import threading
import time
from pathlib import Path

import requests

# =========================
# 상대경로 설정
# =========================
BASE_DIR = Path(__file__).resolve().parent

PAIR_ROOT = BASE_DIR / "data" / "pair"
LEAF_ROOT = BASE_DIR / "data" / "leaf"
FRUIT_ROOT = BASE_DIR / "data" / "fruit"

# =========================
# API 주소
# =========================
PAIR_API = "http://127.0.0.1:8000/api/analysis/upload-images"
LEAF_API = "http://127.0.0.1:8000/api/analysis/infer/leaf"
FRUIT_API = "http://127.0.0.1:8000/api/analysis/infer/fruit"

# =========================
# 생장 단계
# =========================
STAGES = ["growth", "flowering", "fruiting", "ripening", "harvest"]

DELAY_SEC = 1.0
STAGE_CHANGE_CYCLE = 20
TIMEOUT_SEC = 30


# =========================
# stage별 Healthy 비율 유지
# 나머지 비율은 Leaf 하위 병충해 폴더 중 랜덤 선택
# =========================
def get_leaf_ratio(stage: str) -> dict[str, int]:
    if stage == "growth":
        return {"Healthy": 100}
    if stage == "flowering":
        return {"Healthy": 97, "Disease": 3}
    if stage == "fruiting":
        return {"Healthy": 95, "Disease": 5}
    if stage == "ripening":
        return {"Healthy": 90, "Disease": 10}
    return {"Healthy": 85, "Disease": 15}


# =========================
# stage별 열매 상태 이미지 비율
# =========================
def get_fruit_ratio(stage: str) -> dict[str, int] | None:
    if stage in ["growth", "flowering"]:
        return None
    if stage == "fruiting":
        return {"Good": 100}
    if stage == "ripening":
        return {"Good": 98, "Bad": 2}
    return {"Good": 95, "Bad": 5}


def get_random_image(root: Path, class_name: str) -> Path | None:
    class_dir = root / class_name

    if not class_dir.is_dir():
        print(f"폴더 없음: {class_dir}")
        return None

    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    images = [
        p for p in class_dir.iterdir()
        if p.is_file() and p.suffix.lower() in exts
    ]

    if not images:
        print(f"이미지 없음: {class_dir}")
        return None

    return random.choice(images)


def get_leaf_classes() -> list[str]:
    if not LEAF_ROOT.is_dir():
        print(f"LEAF_ROOT 없음: {LEAF_ROOT}")
        return []

    return [p.name for p in LEAF_ROOT.iterdir() if p.is_dir()]


def get_random_leaf_by_ratio(stage: str) -> tuple[str, Path] | None:
    ratio = get_leaf_ratio(stage)

    healthy_ratio = ratio.get("Healthy", 0)

    all_classes = get_leaf_classes()
    disease_classes = [
        class_name for class_name in all_classes
        if class_name != "Healthy"
    ]

    rand = random.randint(1, 100)

    if rand <= healthy_ratio:
        selected_class = "Healthy"
    else:
        if not disease_classes:
            print("병충해 폴더가 없습니다.")
            return None

        selected_class = random.choice(disease_classes)

    img = get_random_image(LEAF_ROOT, selected_class)

    if not img:
        return None

    return selected_class, img


def send_single_image(api_url: str, img_path: Path) -> None:
    with open(img_path, "rb") as f:
        files = {
            "file": (img_path.name, f, "application/octet-stream")
        }
        res = requests.post(api_url, files=files, timeout=TIMEOUT_SEC)

    print(f"  → {res.status_code}")


# =========================
# stage별 pair 폴더 찾기
# data/pair/growth/아무폴더/a1_xxx.png
# data/pair/growth/아무폴더/a4_xxx.png
# data/pair/growth/아무폴더/e_xxx.png
# =========================
def get_stage_pair_folders(stage: str) -> list[Path]:
    stage_root = PAIR_ROOT / stage

    if not stage_root.is_dir():
        print(f"[PAIR] stage 폴더 없음: {stage_root}")
        return []

    folders = sorted([p for p in stage_root.iterdir() if p.is_dir()])

    if not folders:
        print(f"[PAIR] stage 폴더 안에 샘플 폴더 없음: {stage_root}")

    return folders


# =========================
# a1 / a4 / e 묶음 이미지 탐색
# =========================
def find_pair_images(folder: Path) -> tuple[Path | None, Path | None, Path | None]:
    height_image = None
    leaf_metric_image = None
    fruit_set_image = None

    for p in folder.iterdir():
        if not p.is_file():
            continue

        if p.name.startswith("a1_"):
            height_image = p
        elif p.name.startswith("a4_"):
            leaf_metric_image = p
        elif p.name.startswith("e_"):
            fruit_set_image = p

    return height_image, leaf_metric_image, fruit_set_image


def send_pair_images(folder: Path) -> None:
    height_image, leaf_metric_image, fruit_set_image = find_pair_images(folder)

    if not height_image and not leaf_metric_image and not fruit_set_image:
        print(f"[PAIR] 보낼 이미지 없음: {folder.name}")
        return

    files = {}
    opened = []

    try:
        if height_image:
            f = open(height_image, "rb")
            opened.append(f)
            files["plant_image"] = (height_image.name, f, "image/png")

        if leaf_metric_image:
            f = open(leaf_metric_image, "rb")
            opened.append(f)
            files["leaf_image"] = (leaf_metric_image.name, f, "image/png")

        if fruit_set_image:
            f = open(fruit_set_image, "rb")
            opened.append(f)
            files["fruit_image"] = (fruit_set_image.name, f, "image/png")

        data = {
            "folder_name": folder.name,
            "a1_role": "초장",
            "a4_role": "엽장/엽폭/잎개수",
            "e_role": "열매 착생정보",
        }

        res = requests.post(
            PAIR_API,
            files=files,
            data=data,
            timeout=TIMEOUT_SEC,
        )

        print(f"[PAIR] {folder.name}")
        print(f"  a1(초장)             : {height_image.name if height_image else None}")
        print(f"  a4(엽장/엽폭/잎개수): {leaf_metric_image.name if leaf_metric_image else None}")
        print(f"  e(열매 착생정보)     : {fruit_set_image.name if fruit_set_image else None}")
        print(f"  → {res.status_code}")

    except Exception as ex:
        print(f"[PAIR FAIL] {folder.name}: {type(ex).__name__}: {ex}")

    finally:
        for f in opened:
            f.close()


def simulation_loop(stop_event: threading.Event) -> None:
    if not PAIR_ROOT.is_dir():
        print(f"PAIR_ROOT 없음: {PAIR_ROOT}")
        return

    stage_idx = 0
    cycle = 0

    while not stop_event.is_set():
        cycle += 1
        stage = STAGES[stage_idx]

        print(f"\n===== Cycle {cycle} | Stage: {stage} =====")

        # 1) 현재 stage에 맞는 a1/a4/e 묶음 전송
        stage_pair_folders = get_stage_pair_folders(stage)

        if stage_pair_folders:
            pair_folder = random.choice(stage_pair_folders)
            send_pair_images(pair_folder)
        else:
            print(f"[PAIR] {stage} 단계에서 전송할 이미지 없음")

        # 2) 병충해 상태 이미지 전송
        # Healthy 비율 유지, Disease면 하위 병충해 폴더 랜덤 선택
        for _ in range(3):
            if stop_event.is_set():
                break

            result = get_random_leaf_by_ratio(stage)

            if result:
                class_name, img = result
                print(f"[LEAF 병충해 상태] {class_name} → {img.name}")

                try:
                    send_single_image(LEAF_API, img)
                except Exception as ex:
                    print(f"[LEAF FAIL] {class_name}: {type(ex).__name__}: {ex}")

        # 3) 열매 상태 이미지 전송
        fruit_ratio = get_fruit_ratio(stage)

        if fruit_ratio is None:
            print("[FRUIT 열매 상태] 현재 단계에서는 열매 상태 이미지 전송 없음")
        else:
            fruit_schedule = []
            for class_name, count in fruit_ratio.items():
                fruit_schedule.extend([class_name] * count)

            random.shuffle(fruit_schedule)

            for class_name in fruit_schedule[:2]:
                if stop_event.is_set():
                    break

                img = get_random_image(FRUIT_ROOT, class_name)

                if img:
                    print(f"[FRUIT 열매 상태] {class_name} → {img.name}")

                    try:
                        send_single_image(FRUIT_API, img)
                    except Exception as ex:
                        print(f"[FRUIT FAIL] {class_name}: {type(ex).__name__}: {ex}")

        # 4) 생장 단계 변경
        if cycle % STAGE_CHANGE_CYCLE == 0 and stage_idx < len(STAGES) - 1:
            stage_idx += 1
            print(f"\n➡️ Stage 변경: {STAGES[stage_idx]}")

        time.sleep(DELAY_SEC)

    print("시뮬 종료")


def main() -> None:
    print("===== SeedFarm CCTV 이미지 시뮬레이터 =====")
    print("a1_* = 초장")
    print("a4_* = 엽장 / 엽폭 / 잎 개수")
    print("e_*  = 열매 착생정보")
    print("Leaf/Healthy = 정상 잎")
    print("Leaf/기타 폴더 = 병충해 랜덤 후보")
    print("Tomato/Good, Tomato/Bad = 열매 상태")
    print()
    print("PAIR_ROOT 구조:")
    print("data/pair/growth/아무폴더/a1_xxx.png")
    print("data/pair/growth/아무폴더/a4_xxx.png")
    print("data/pair/growth/아무폴더/e_xxx.png")
    print()
    print(f"PAIR_ROOT : {PAIR_ROOT}")
    print(f"LEAF_ROOT : {LEAF_ROOT}")
    print(f"FRUIT_ROOT: {FRUIT_ROOT}")
    print("종료하려면 s 입력 후 Enter")

    stop_event = threading.Event()

    t = threading.Thread(target=simulation_loop, args=(stop_event,), daemon=True)
    t.start()

    while True:
        cmd = input().strip().lower()

        if cmd == "s":
            stop_event.set()
            t.join()
            print("전체 종료 완료")
            break


if __name__ == "__main__":
    main()