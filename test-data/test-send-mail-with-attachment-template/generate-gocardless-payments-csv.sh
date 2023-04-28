#!/usr/bin/env bash
set -euf -o pipefail
script_dir="${BASH_SOURCE[0]%/*}"
repo_dir="$(cd "${script_dir}/../.." && pwd)"
build_dir="${repo_dir}/build"

poetry install --directory="${repo_dir}"

mkdir -p "${build_dir}"
output_dir="$(mktemp --directory --tmpdir="${build_dir}" -t tmp.XXXXXXXXXX.test-results)"

poetry run --directory "${repo_dir}" -- \
    generate-gocardless-payments-csv \
        --input-invoice-requests-csv="${script_dir}/invoice-requests.csv" \
        --input-gocardless-customers-csv="${script_dir}/gocardless-customers.csv" \
        --invoice-customer-id-field="parent_id" \
        --invoice-total-amount-field="amount_due" \
        --invoice-payment-method-field="payment_method" \
        --invoice-payment-method-value="GoCardless" \
        --invoice-id-prefix="abc-summer23" \
        --output-gocardless-payments-csv="${output_dir}/gocardless-payments.csv"
