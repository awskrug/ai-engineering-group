#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import re


# 정규식을 이용하여 이메일과 전화번호 추출
email_pattern = re.compile(r"[\w\.-]+@[\w\.-]+")
phone_pattern = re.compile(r"010-\d{4}-\d{4}")


def parse_args():
    p = argparse.ArgumentParser(description="csv converter")
    p.add_argument("-i", "--input", default="input.xls", help="input file")
    p.add_argument("-o", "--output", default="output.csv", help="output file")
    return p.parse_args()


def process_file(input_file, output_file):
    try:
        with open(input_file, "r", encoding="utf-8") as file:
            lines = file.readlines()

        if not lines:
            print(f"Error: {input_file} is empty")
            return

        # 첫 번째 줄 삭제
        lines = lines[1:]
    except FileNotFoundError:
        print(f"Error: {input_file} not found")
        return
    except Exception as e:
        print(f"Error reading file: {str(e)}")
        return

    processed_data = []

    for line in lines:
        # ₩가 포함된 줄만 처리
        if "₩" in line:
            match = re.match(r"^(.*?)\s+user", line)
            if match:
                real_name = match.group(1).strip()
            else:
                real_name = line.split("\t")[0]

            # URL과 URL 앞의 문자 삭제
            line = re.sub(
                r".*?(https://www\.meetup\.com/ko-KR/awskrug/members/\d+/?)", "", line
            )

            # 모든 공백 제거
            line = line.replace(" ", "").strip()

            # 전화번호 형식 변환
            line = re.sub(r"(\d{3})(\d{4})(\d{4})", r"\1-\2-\3", line)

            # 이메일과 전화번호 추출
            emails = email_pattern.findall(line)
            email = emails[0] if emails else ""

            phones = phone_pattern.findall(line)
            phone = phones[0] if phones else ""

            # 이름과 회사 추출
            parts = line.split("/")

            name = (
                parts[0]
                if len(parts) > 1 and "@" not in parts[0] and "010-" not in parts[0]
                else real_name
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
