#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import pandas as pd
import csv
import re


# 정규식을 이용하여 이메일과 전화번호 추출
email_pattern = re.compile(r"[\w\.-]+@[\w\.-]+")
phone_pattern = re.compile(r"010-\d{4}-\d{4}")


def parse_args():
    p = argparse.ArgumentParser(description="attendee converter")
    p.add_argument("-i", "--input", default="input.csv", help="input file")
    p.add_argument("-o", "--output", default="output.csv", help="output file")
    return p.parse_args()


def process_file(input_file, output_file):
    data = pd.read_csv(input_file)

    # 23번째 필드에 값이 있는 행 필터링
    filtered_data = data[data.iloc[:, 23].notna() & (data.iloc[:, 23] != "")]

    # 25번째 필드 값 추출
    names = filtered_data.iloc[:, 0]
    field_25_values = filtered_data.iloc[:, 25]

    processed_data = []

    for name, value in zip(names, field_25_values):
        # NaN 값 체크
        if pd.isna(value) or value == "":
            continue

        # 문자열로 변환하고 모든 공백 제거
        value = str(value).replace(" ", "").strip()

        # 전화번호 형식 변환
        value = re.sub(r"(\d{3})(\d{4})(\d{4})", r"\1-\2-\3", value)

        # 이메일과 전화번호 추출
        emails = email_pattern.findall(value)
        email = emails[0] if emails else ""

        phones = phone_pattern.findall(value)
        phone = phones[0] if phones else ""

        # 이름과 회사 추출
        parts = value.split("/")

        name = (
            parts[0]
            if len(parts) > 1 and "@" not in parts[0] and "010-" not in parts[0]
            else name
        )

        company = (
            parts[1]
            if len(parts) > 2 and "@" not in parts[1] and "010-" not in parts[1]
            else ""
        )

        # 결과 추가
        processed_data.append(f"{name},{company},{email},{phone}")

        print(f"{name},{company},{email},{phone}")

    # CSV 파일로 저장
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        for data in processed_data:
            writer.writerow(data.split(","))


def main():
    args = parse_args()

    # 파일 처리
    process_file(args.input, args.output)


if __name__ == "__main__":
    main()
