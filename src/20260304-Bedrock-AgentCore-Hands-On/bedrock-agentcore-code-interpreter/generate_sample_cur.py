#!/usr/bin/env python3
"""
CUR (Cost and Usage Report) 샘플 데이터 생성 스크립트

실제 CUR 리포트와 동일한 컬럼 구조를 가진 가상 데이터를 생성합니다.
워크숍에서 demo-cur-00001.csv 대신 사용할 수 있습니다.

사용법:
    python3 generate_sample_cur.py                    # 기본 98행
    python3 generate_sample_cur.py --rows 200         # 200행
    python3 generate_sample_cur.py -o my_cur.csv      # 출력 파일 지정
"""

import argparse
import csv
import hashlib
import io
import random
import uuid
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# 서비스 정의: (ProductCode, ProductName, servicename, servicecode)
# ---------------------------------------------------------------------------
SERVICES = [
    ("AmazonEC2", "Amazon Elastic Compute Cloud", "Amazon Elastic Compute Cloud", "AmazonEC2"),
    ("AmazonS3", "Amazon Simple Storage Service", "Amazon Simple Storage Service", "AmazonS3"),
    ("AWSLambda", "AWS Lambda", "AWS Data Transfer", "AWSDataTransfer"),
    ("awskms", "AWS Key Management Service", "AWS Key Management Service", "awskms"),
    ("AmazonDynamoDB", "Amazon DynamoDB", "Amazon DynamoDB", "AmazonDynamoDB"),
    ("AmazonGuardDuty", "Amazon GuardDuty", "Amazon GuardDuty", "AmazonGuardDuty"),
    ("AWSCloudTrail", "AWS CloudTrail", "AWS CloudTrail", "AWSCloudTrail"),
    ("AWSGlue", "AWS Glue", "AWS Glue", "AWSGlue"),
    ("AmazonSNS", "Amazon Simple Notification Service", "Amazon Simple Notification Service", "AmazonSNS"),
    ("AmazonDataZone", "Amazon DataZone", "Amazon DataZone", "AmazonDataZone"),
]

# 서비스별 비용 가중치 (EC2가 가장 비쌈)
SERVICE_WEIGHTS = [40, 8, 5, 15, 3, 4, 2, 3, 1, 2]

# 서비스별 대표 Operation
SERVICE_OPERATIONS = {
    "AmazonEC2": ["RunInstances", "NatGateway", "PublicIP-In"],
    "AmazonS3": ["StandardStorage", "GetObject", "PutObject"],
    "AWSLambda": ["Invoke", "ReadACL"],
    "awskms": ["CurrentKeys", "RotatedKeys", "GenerateDataKey"],
    "AmazonDynamoDB": ["TablesObjects", "Storage", "GetItem"],
    "AmazonGuardDuty": ["MonitorUsage", "AnalyzeFlowLogs"],
    "AWSCloudTrail": ["LookupEvents", "CreateTrail"],
    "AWSGlue": ["CrawlerRun", "JobRun"],
    "AmazonSNS": ["ListTopics", "Publish"],
    "AmazonDataZone": ["Global-DataZoneStorage", "DataZoneAccess"],
}

# 서비스별 대표 UsageType
SERVICE_USAGE_TYPES = {
    "AmazonEC2": ["USE1-BoxUsage:t3.medium", "USE1-NatGateway-Hours", "USE1-PublicIPv4:InUseAddress"],
    "AmazonS3": ["USE1-TimedStorage-ByteHrs", "USE1-Requests-Tier1", "USE1-Requests-Tier2"],
    "AWSLambda": ["USE1-EUC1-AWS-Out-Bytes", "USE1-Lambda-GB-Second"],
    "awskms": ["USE1-KMS-Keys", "USE1-KMS-Requests"],
    "AmazonDynamoDB": ["USE1-TimedStorage-ByteHrs", "USE1-ReadCapacityUnit-Hrs"],
    "AmazonGuardDuty": ["USE1-GuardDuty-VPCFlowLogs", "USE1-GuardDuty-DNSLogs"],
    "AWSCloudTrail": ["USE1-DataEventsRecorded", "USE1-ManagementEventsRecorded"],
    "AWSGlue": ["USE1-Crawler-DPU-Hour", "USE1-ETL-DPU-Hour"],
    "AmazonSNS": ["USE1-DeliveryAttempts-HTTP", "USE1-Requests-Tier1"],
    "AmazonDataZone": ["USE1-DataZone-Storage-ByteHrs", "USE1-DataZone-Access"],
}

# 서비스별 비용 범위 (min, max)
SERVICE_COST_RANGES = {
    "AmazonEC2": (0.01, 1.10),
    "AmazonS3": (0.0000001, 0.005),
    "AWSLambda": (0.0000001, 0.001),
    "awskms": (0.001, 0.15),
    "AmazonDynamoDB": (0.0000001, 0.01),
    "AmazonGuardDuty": (0.0001, 0.005),
    "AWSCloudTrail": (0.0, 0.001),
    "AWSGlue": (0.0, 0.005),
    "AmazonSNS": (0.0, 0.0001),
    "AmazonDataZone": (0.0, 0.002),
}

REGIONS = [
    ("US East (N. Virginia)", "us-east-1"),
    ("US West (Oregon)", "us-west-2"),
    ("Asia Pacific (Tokyo)", "ap-northeast-1"),
    ("Asia Pacific (Seoul)", "ap-northeast-2"),
    ("Asia Pacific (Osaka)", "ap-northeast-3"),
    ("Asia Pacific (Mumbai)", "ap-south-1"),
    ("Asia Pacific (Sydney)", "ap-southeast-2"),
    ("Europe (Frankfurt)", "eu-central-1"),
    ("Europe (Stockholm)", "eu-north-1"),
]

TRANSFER_PAIRS = [
    ("US East (N. Virginia)", "us-east-1", "EU (Frankfurt)", "eu-central-1"),
    ("US East (N. Virginia)", "us-east-1", "Asia Pacific (Tokyo)", "ap-northeast-1"),
    ("Asia Pacific (Tokyo)", "ap-northeast-1", "Asia Pacific (Seoul)", "ap-northeast-2"),
]

PAYER_ACCOUNT = "123456789012"
USAGE_ACCOUNT = "234567890123"

# CUR 전체 컬럼 목록
COLUMNS = [
    "identity/LineItemId", "identity/TimeInterval",
    "bill/InvoiceId", "bill/InvoicingEntity", "bill/BillingEntity", "bill/BillType",
    "bill/PayerAccountId", "bill/BillingPeriodStartDate", "bill/BillingPeriodEndDate",
    "lineItem/UsageAccountId", "lineItem/LineItemType",
    "lineItem/UsageStartDate", "lineItem/UsageEndDate",
    "lineItem/ProductCode", "lineItem/UsageType", "lineItem/Operation",
    "lineItem/AvailabilityZone", "lineItem/UsageAmount",
    "lineItem/NormalizationFactor", "lineItem/NormalizedUsageAmount",
    "lineItem/CurrencyCode", "lineItem/UnblendedRate", "lineItem/UnblendedCost",
    "lineItem/BlendedRate", "lineItem/BlendedCost",
    "lineItem/LineItemDescription", "lineItem/TaxType", "lineItem/LegalEntity",
    "product/ProductName",
]

# product/* 컬럼 (대부분 빈 값이지만 구조 유지)
PRODUCT_COLUMNS = [
    "product/alarmType", "product/architecture", "product/availability",
    "product/availabilityZone", "product/cacheType", "product/capacitystatus",
    "product/category", "product/ciType", "product/classicnetworkingsupport",
    "product/clockSpeed", "product/cloudformationresourceProvider",
    "product/component", "product/computeFamily", "product/computeType",
    "product/currentGeneration", "product/databaseEngine",
    "product/datastoreStoragetype", "product/dedicatedEbsThroughput",
    "product/dedicatedEbsThroughputDescription", "product/deploymentOption",
    "product/description", "product/durability", "product/duration",
    "product/ecu", "product/edition", "product/endpointType",
    "product/engineCode", "product/enhancedNetworkingSupported",
    "product/eventType", "product/feature", "product/featureType",
    "product/feeCode", "product/feeDescription", "product/fileSystemType",
    "product/findingGroup", "product/findingSource", "product/findingStorage",
    "product/freeQueryTypes", "product/fromLocation", "product/fromLocationType",
    "product/fromRegionCode", "product/gpu", "product/gpuMemory",
    "product/group", "product/groupDescription", "product/imagequality",
    "product/imageresolution", "product/inferenceType", "product/instanceFamily",
    "product/instanceName", "product/instanceType", "product/instanceTypeFamily",
    "product/intelAvx2Available", "product/intelAvxAvailable",
    "product/intelTurboAvailable", "product/jobType", "product/licenseModel",
    "product/location", "product/locationType", "product/logsDestination",
    "product/m2mCategory", "product/marketoption", "product/maxIopsvolume",
    "product/maxThroughputvolume", "product/maxVolumeSize", "product/memory",
    "product/messageDeliveryFrequency", "product/messageDeliveryOrder",
    "product/minVolumeSize", "product/model", "product/networkPerformance",
    "product/normalizationSizeFactor", "product/operatingSystem",
    "product/operation", "product/packSize", "product/physicalCpu",
    "product/physicalGpu", "product/physicalProcessor",
    "product/platoclassificationtype", "product/platoinstancename",
    "product/platoinstancetype", "product/platopricingtype",
    "product/preInstalledSw", "product/pricingplan",
    "product/processorArchitecture", "product/processorFeatures",
    "product/productFamily", "product/provider", "product/qPresent",
    "product/queueType", "product/region", "product/regionCode",
    "product/resource", "product/servicecode", "product/servicename",
    "product/sku", "product/standardGroup", "product/standardStorage",
    "product/steps", "product/storage", "product/storageClass",
    "product/storageMedia", "product/storageTier", "product/storageType",
    "product/subcategory", "product/subscriptionType", "product/subservice",
    "product/tenancy", "product/throughputCapacity", "product/tiertype",
    "product/titanModel", "product/toLocation", "product/toLocationType",
    "product/toRegionCode", "product/transferType", "product/type",
    "product/usageGroup", "product/usagetype", "product/vcpu",
    "product/version", "product/volumeApiName", "product/volumeType",
    "product/vpcnetworkingsupport",
]

PRICING_COLUMNS = [
    "pricing/RateCode", "pricing/RateId", "pricing/currency",
    "pricing/publicOnDemandCost", "pricing/publicOnDemandRate",
    "pricing/term", "pricing/unit",
]

RESERVATION_COLUMNS = [
    "reservation/AmortizedUpfrontCostForUsage",
    "reservation/AmortizedUpfrontFeeForBillingPeriod",
    "reservation/EffectiveCost", "reservation/EndTime",
    "reservation/ModificationStatus",
    "reservation/NormalizedUnitsPerReservation",
    "reservation/NumberOfReservations",
    "reservation/RecurringFeeForUsage", "reservation/StartTime",
    "reservation/SubscriptionId",
    "reservation/TotalReservedNormalizedUnits",
    "reservation/TotalReservedUnits", "reservation/UnitsPerReservation",
    "reservation/UnusedAmortizedUpfrontFeeForBillingPeriod",
    "reservation/UnusedNormalizedUnitQuantity",
    "reservation/UnusedQuantity", "reservation/UnusedRecurringFee",
    "reservation/UpfrontValue",
]

SAVINGS_PLAN_COLUMNS = [
    "savingsPlan/TotalCommitmentToDate", "savingsPlan/SavingsPlanARN",
    "savingsPlan/SavingsPlanRate", "savingsPlan/UsedCommitment",
    "savingsPlan/SavingsPlanEffectiveCost",
    "savingsPlan/AmortizedUpfrontCommitmentForBillingPeriod",
    "savingsPlan/RecurringCommitmentForBillingPeriod",
]

RESOURCE_TAG_COLUMNS = [
    "resourceTags/user:AmazonDataZoneBlueprint",
    "resourceTags/user:AmazonDataZoneDomain",
    "resourceTags/user:AmazonDataZoneDomainAccount",
    "resourceTags/user:AmazonDataZoneDomainRegion",
    "resourceTags/user:AmazonDataZoneEnvironment",
    "resourceTags/user:AmazonDataZoneProject",
    "resourceTags/user:sagemaker:domain-arn",
]

ALL_COLUMNS = (
    COLUMNS + PRODUCT_COLUMNS + PRICING_COLUMNS
    + RESERVATION_COLUMNS + SAVINGS_PLAN_COLUMNS + RESOURCE_TAG_COLUMNS
)


def _random_line_item_id() -> str:
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:50]


def _random_sku() -> str:
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(random.choice(chars) for _ in range(16))


def generate_row(
    billing_start: datetime,
    billing_end: datetime,
    day_offset: int,
) -> dict:
    """1개의 CUR 행 생성"""
    row = {col: "" for col in ALL_COLUMNS}

    # 서비스 선택 (가중치 기반)
    svc_idx = random.choices(range(len(SERVICES)), weights=SERVICE_WEIGHTS, k=1)[0]
    product_code, product_name, service_name, service_code = SERVICES[svc_idx]

    # 날짜
    usage_start = billing_start + timedelta(days=day_offset)
    usage_end = usage_start + timedelta(days=1)
    time_interval = f"{usage_start.strftime('%Y-%m-%dT%H:%M:%SZ')}/{usage_end.strftime('%Y-%m-%dT%H:%M:%SZ')}"

    # 비용
    cost_min, cost_max = SERVICE_COST_RANGES[product_code]
    cost = round(random.uniform(cost_min, cost_max), 10)
    usage_amount = round(random.uniform(0.0000001, 1.0), 10)
    rate = round(cost / usage_amount if usage_amount > 0 else 0, 10)

    # 리전
    location_name, region_code = random.choice(REGIONS)
    operation = random.choice(SERVICE_OPERATIONS[product_code])
    usage_type = random.choice(SERVICE_USAGE_TYPES[product_code])

    # 데이터 전송 행인 경우
    is_transfer = "Out-Bytes" in usage_type or "AWS-Out" in usage_type
    to_location, to_region = "", ""
    transfer_type = ""
    if is_transfer and TRANSFER_PAIRS:
        pair = random.choice(TRANSFER_PAIRS)
        location_name, region_code = pair[0], pair[1]
        to_location, to_region = pair[2], pair[3]
        transfer_type = "InterRegion Outbound"

    sku = _random_sku()
    rate_code = f"{sku}.JRTCKXETXF.6YS6EN2CT7"
    rate_id = str(random.randint(100000000000, 999999999999))

    # identity
    row["identity/LineItemId"] = _random_line_item_id()
    row["identity/TimeInterval"] = time_interval

    # bill
    row["bill/InvoicingEntity"] = "Amazon Web Services, Inc."
    row["bill/BillingEntity"] = "AWS"
    row["bill/BillType"] = "Anniversary"
    row["bill/PayerAccountId"] = PAYER_ACCOUNT
    row["bill/BillingPeriodStartDate"] = billing_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    row["bill/BillingPeriodEndDate"] = billing_end.strftime("%Y-%m-%dT%H:%M:%SZ")

    # lineItem
    row["lineItem/UsageAccountId"] = USAGE_ACCOUNT
    row["lineItem/LineItemType"] = "Usage"
    row["lineItem/UsageStartDate"] = usage_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    row["lineItem/UsageEndDate"] = usage_end.strftime("%Y-%m-%dT%H:%M:%SZ")
    row["lineItem/ProductCode"] = product_code
    row["lineItem/UsageType"] = usage_type
    row["lineItem/Operation"] = operation
    row["lineItem/AvailabilityZone"] = region_code.split("-")[0] + "-" + region_code.split("-")[1] + "-1" if product_code == "AmazonEC2" else ""
    row["lineItem/UsageAmount"] = f"{usage_amount:.10f}"
    row["lineItem/CurrencyCode"] = "USD"
    row["lineItem/UnblendedRate"] = f"{rate:.10f}"
    row["lineItem/UnblendedCost"] = f"{cost:.10f}"
    row["lineItem/BlendedRate"] = f"{rate:.10f}"
    row["lineItem/BlendedCost"] = f"{cost:.10f}"
    row["lineItem/LineItemDescription"] = f"${rate:.2f} per unit - {location_name}"
    row["lineItem/LegalEntity"] = "Amazon Web Services, Inc."

    # product (주요 필드만)
    row["product/ProductName"] = product_name
    row["product/location"] = location_name
    row["product/locationType"] = "AWS Region"
    row["product/regionCode"] = region_code
    row["product/region"] = location_name
    row["product/servicecode"] = service_code
    row["product/servicename"] = service_name
    row["product/sku"] = sku
    if is_transfer:
        row["product/fromLocation"] = location_name
        row["product/fromLocationType"] = "AWS Region"
        row["product/fromRegionCode"] = region_code
        row["product/toLocation"] = to_location
        row["product/toLocationType"] = "AWS Region"
        row["product/toRegionCode"] = to_region
        row["product/transferType"] = transfer_type
        row["product/productFamily"] = "Data Transfer"
    row["product/usagetype"] = usage_type

    # pricing
    row["pricing/RateCode"] = rate_code
    row["pricing/RateId"] = rate_id
    row["pricing/currency"] = "USD"
    row["pricing/publicOnDemandCost"] = f"{cost:.10f}"
    row["pricing/publicOnDemandRate"] = f"{rate:.10f}"
    row["pricing/term"] = "OnDemand"
    row["pricing/unit"] = "GB" if is_transfer else "Hrs"

    return row


def generate_cur_csv(
    num_rows: int = 98,
    billing_year: int = 2026,
    billing_month: int = 1,
    seed: int = 42,
) -> str:
    """CUR CSV 문자열 생성"""
    random.seed(seed)

    billing_start = datetime(billing_year, billing_month, 1)
    if billing_month == 12:
        billing_end = datetime(billing_year + 1, 1, 1)
    else:
        billing_end = datetime(billing_year, billing_month + 1, 1)

    days_in_period = (billing_end - billing_start).days

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=ALL_COLUMNS)
    writer.writeheader()

    for _ in range(num_rows):
        day_offset = random.randint(0, min(days_in_period - 1, 12))
        row = generate_row(billing_start, billing_end, day_offset)
        writer.writerow(row)

    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(
        description="CUR 샘플 데이터 생성기"
    )
    parser.add_argument(
        "--rows", type=int, default=98,
        help="생성할 행 수 (기본: 98)"
    )
    parser.add_argument(
        "-o", "--output", type=str, default="demo-cur-00001.csv",
        help="출력 파일 경로 (기본: demo-cur-00001.csv)"
    )
    parser.add_argument(
        "--year", type=int, default=2026,
        help="빌링 연도 (기본: 2026)"
    )
    parser.add_argument(
        "--month", type=int, default=1,
        help="빌링 월 (기본: 1)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="랜덤 시드 (기본: 42)"
    )
    args = parser.parse_args()

    csv_content = generate_cur_csv(
        num_rows=args.rows,
        billing_year=args.year,
        billing_month=args.month,
        seed=args.seed,
    )

    with open(args.output, "w", newline="") as f:
        f.write(csv_content)

    # 요약 출력
    import csv as csv_mod
    reader = csv_mod.DictReader(io.StringIO(csv_content))
    rows = list(reader)
    total_cost = sum(float(r.get("lineItem/UnblendedCost", 0) or 0) for r in rows)
    services = set(r.get("lineItem/ProductCode", "") for r in rows)

    print(f"✅ {args.output} 생성 완료")
    print(f"   행 수: {len(rows)}")
    print(f"   서비스 수: {len(services)}")
    print(f"   총 비용: ${total_cost:.6f}")
    print(f"   빌링 기간: {args.year}-{args.month:02d}")
    print(f"   서비스: {', '.join(sorted(services))}")


if __name__ == "__main__":
    main()
