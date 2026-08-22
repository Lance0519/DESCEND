"""
Demo: generate synthetic grouped dataset and perform stratified 80/20 group holdout split.
Saves `demo_train.csv` and `demo_test.csv` into the same folder and prints summary counts.
"""
import csv
import random
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
TRAIN_OUT = OUT_DIR / "demo_train.csv"
TEST_OUT = OUT_DIR / "demo_test.csv"

TARGET = "outcome"
GROUP = "family_id"


def stratified_group_holdout_split(rows, test_size=0.2, seed=42):
    grouped_rows = {}
    for index, row in enumerate(rows):
        group_key = int(row[GROUP])
        grouped_rows.setdefault(group_key, []).append(row)

    positive_groups = []
    negative_groups = []

    for group_key, group_items in grouped_rows.items():
        labels = {int(item[TARGET]) for item in group_items}
        if len(labels) != 1:
            raise ValueError(f"Group {group_key} has mixed labels.")
        group_label = next(iter(labels))
        if group_label == 1:
            positive_groups.append(group_items)
        else:
            negative_groups.append(group_items)

    if not positive_groups or not negative_groups:
        raise ValueError("Need at least one positive and one negative group.")

    rng = random.Random(seed)
    rng.shuffle(positive_groups)
    rng.shuffle(negative_groups)

    pos_test_count = max(1, int(round(len(positive_groups) * test_size)))
    neg_test_count = max(1, int(round(len(negative_groups) * test_size)))

    train_rows = []
    test_rows = []

    for group_items in positive_groups[pos_test_count:] + negative_groups[neg_test_count:]:
        train_rows.extend(group_items)

    for group_items in positive_groups[:pos_test_count] + negative_groups[:neg_test_count]:
        test_rows.extend(group_items)

    rng.shuffle(train_rows)
    rng.shuffle(test_rows)

    return train_rows, test_rows


def generate_synthetic_dataset(n_groups=60, min_per_group=1, max_per_group=3, pos_group_frac=0.35, seed=42):
    rng = random.Random(seed)
    rows = []
    group_id = 1
    for g in range(n_groups):
        # assign group-level label
        is_pos = 1 if rng.random() < pos_group_frac else 0
        size = rng.randint(min_per_group, max_per_group)
        for i in range(size):
            row = {
                GROUP: group_id,
                TARGET: is_pos,
                "age": round(rng.uniform(18, 80), 1),
                "bmi": round(rng.uniform(18, 40), 2),
                "user_is_male": rng.choice([0, 1]),
            }
            rows.append(row)
        group_id += 1
    return rows


def write_csv(path, rows):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


if __name__ == "__main__":
    rows = generate_synthetic_dataset(n_groups=60, min_per_group=1, max_per_group=4, pos_group_frac=0.35, seed=42)
    train, test = stratified_group_holdout_split(rows, test_size=0.2, seed=42)

    def summary(xs):
        total = len(xs)
        pos = sum(1 for r in xs if int(r[TARGET]) == 1)
        neg = total - pos
        groups = len(set(int(r[GROUP]) for r in xs))
        return total, pos, neg, groups

    t_total, t_pos, t_neg, t_groups = summary(train)
    s_total, s_pos, s_neg, s_groups = summary(test)

    print("Demo stratified-group 80/20 split (synthetic data):")
    print(f"  Total rows generated: {len(rows)}")
    print(f"  Train rows: {t_total} (pos={t_pos}, neg={t_neg}, groups={t_groups})")
    print(f"  Test rows:  {s_total} (pos={s_pos}, neg={s_neg}, groups={s_groups})")
    print("\nSample train rows:")
    for r in train[:5]:
        print(f"  {r}")
    print("\nSample test rows:")
    for r in test[:5]:
        print(f"  {r}")

    write_csv(TRAIN_OUT, train)
    write_csv(TEST_OUT, test)
    print(f"\nWrote: {TRAIN_OUT}")
    print(f"Wrote: {TEST_OUT}")
